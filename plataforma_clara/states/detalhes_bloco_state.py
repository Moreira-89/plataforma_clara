"""
Estado de detalhes de um Bloco de Liquidez específico.

Busca dados agregados do bloco selecionado (via parâmetro de rota) no banco
PostgreSQL (Supabase) e disponibiliza para exibição na página de detalhes.
"""

import asyncio
import hashlib
import logging
import urllib.parse
from typing import Any

import reflex as rx
import sqlalchemy as sa

from plataforma_clara.states.dashboard_state import DashboardState

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ESTADO DE DETALHES DO BLOCO
# -----------------------------------------------------------------------------


class DetalhesBlocoState(DashboardState):
    """
    Estado para a página de detalhes de um bloco de liquidez específico.

    Herda DashboardState para manter a sessão de usuário e as permissões.
    Armazena os KPIs do bloco e a lista de empresas financiadas após o carregamento.
    """

    nome_bloco: str = ""
    volume_total: str = ""
    rentabilidade_alvo: str = ""
    score_medio: str = ""
    prazo_medio: str = ""
    empresas_bloco: list[dict[str, Any]] = []

    # -----------------------------------------------------------------------------
    # EVENTOS PÚBLICOS
    # -----------------------------------------------------------------------------

    @rx.event
    async def carregar_detalhes(self):
        """
        Lê o parâmetro de rota e carrega os dados do bloco de forma assíncrona.

        COMO FUNCIONA:
            1. Leitura do Parâmetro — Obtém bloco_id dos parâmetros de rota (URL).
               O Reflex pode devolver o parâmetro como lista em alguns casos,
               por isso usamos a lógica de unwrap [0] se for list.
            2. Validação — Se o bloco_id estiver vazio, inicializa com valores padrão.
            3. Decodificação — URL-decode do nome do bloco (pode ter espaços/caracteres especiais).
            4. Busca em Thread — _buscar_dados_bloco_bq() é CPU-bound (query SQL + cálculos);
               asyncio.to_thread libera o event loop enquanto executa.
            5. Atualização do Estado — Distribui os resultados para as variáveis de KPI.
        """
        # --- 1. LEITURA DO PARÂMETRO ---
        # router.page.params é o único caminho suportado para ler parâmetros de
        # rota dinâmica em event handlers. O DeprecationWarning sobre router.page
        # refere-se ao sub-objeto completo (ex: router.page.path), não ao .params.
        bloco_id_raw = self.router.page.params.get("bloco_id", "")
        bloco_id = (
            bloco_id_raw[0]
            if isinstance(bloco_id_raw, list) and bloco_id_raw
            else bloco_id_raw
        )

        # --- 2. VALIDAÇÃO ---
        if not bloco_id:
            self.nome_bloco = ""
            self.empresas_bloco = []
            self.volume_total = "R$ 0,00"
            self.score_medio = "N/A"
            self.rentabilidade_alvo = "N/A"
            self.prazo_medio = "N/A"
            return

        # --- 3. DECODIFICAÇÃO ---
        bloco_decodificado = urllib.parse.unquote(str(bloco_id))
        self.nome_bloco = bloco_decodificado

        # --- 4. BUSCA EM THREAD ---
        try:
            resultados = await asyncio.to_thread(
                self._buscar_dados_bloco_bq, bloco_decodificado
            )
        except Exception:
            logger.exception("Erro ao carregar detalhes do bloco: %s", bloco_decodificado)
            return

        # --- 5. ATUALIZAÇÃO DO ESTADO ---
        self.empresas_bloco = resultados.get("empresas", [])
        self.volume_total = resultados.get("volume_total", "R$ 0,00")
        self.score_medio = resultados.get("score_medio", "N/A")
        self.rentabilidade_alvo = resultados.get("rentabilidade_alvo", "N/A")
        self.prazo_medio = resultados.get("prazo_medio", "N/A")

    # -----------------------------------------------------------------------------
    # MÉTODOS INTERNOS
    # -----------------------------------------------------------------------------

    def _buscar_dados_bloco_bq(self, bloco: str) -> dict:
        """
        Executa a query no PostgreSQL e formata os resultados para exibição.

        COMO FUNCIONA:
            1. Query SQL — Agrupa os aportes do bloco por empresa sacada.
            2. Cálculos Agregados — Calcula volume total, score médio e prazo médio
               a partir dos resultados, sem novo round-trip ao banco.
            3. Formatação das Empresas — Converte valores numéricos para padrão
               brasileiro e calcula o peso percentual de cada empresa no bloco.
            4. Nota Geral — Traduz o score médio numérico para classificação literal.
            5. Rentabilidade Estável — Hash SHA-1 do nome garante que o mesmo bloco
               exiba sempre o mesmo percentual entre re-renders.

        Args:
            bloco (str): Nome do bloco já URL-decoded para usar no filtro SQL.

        Returns:
            dict: Com chaves volume_total, score_medio, prazo_medio,
                  rentabilidade_alvo e empresas (lista de dicts).
        """
        # --- 1. QUERY SQL ---
        query = sa.text("""
            SELECT
                empresa_sacada_nome,
                cnpj_sacado_limpo,
                SUM(valor_mercado_atual)        AS valor_alocado,
                AVG(score_risco_interno)        AS score,
                COALESCE(AVG(prazo_vencimento_dias), 0) AS prazo_medio
            FROM tb_aporte
            WHERE bloco_liquidez_setorial = :bloco
            GROUP BY empresa_sacada_nome, cnpj_sacado_limpo
            ORDER BY valor_alocado DESC
        """)

        with rx.session() as session:
            result = session.execute(query, {"bloco": bloco}).mappings().fetchall()

        dados_db = [dict(row) for row in result]

        if not dados_db:
            return {}

        # --- 2. CÁLCULOS AGREGADOS ---
        total_vol = sum(float(r["valor_alocado"] or 0.0) for r in dados_db)
        qtd = len(dados_db)
        score_med = sum(float(r["score"] or 0.0) for r in dados_db) / qtd if qtd > 0 else 0
        prazo_med = sum(float(r["prazo_medio"] or 0.0) for r in dados_db) / qtd if qtd > 0 else 0

        # --- 3. FORMATAÇÃO DAS EMPRESAS ---
        empresas = []
        for row in dados_db:
            val = float(row["valor_alocado"] or 0.0)
            # Peso percentual da empresa em relação ao volume total do bloco.
            peso = val / total_vol if total_vol > 0 else 0
            sc = float(row["score"] or 0.0)

            nota = "C-"
            if sc >= 80:
                nota = "A+"
            elif sc >= 70:
                nota = "A"
            elif sc >= 60:
                nota = "A-"
            elif sc >= 50:
                nota = "B+"
            elif sc >= 40:
                nota = "B"

            # Converte para padrão brasileiro: 1.234.567,89
            v_str = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            empresas.append({
                "nome": str(row["empresa_sacada_nome"]),
                "cnpj": str(row["cnpj_sacado_limpo"]),
                "peso": f"{peso * 100:.1f}%",
                "valor": f"R$ {v_str}",
                "score": nota,
            })

        # --- 4. NOTA GERAL ---
        nota_geral = "C- (Alto Risco)"
        if score_med >= 80:
            nota_geral = "A+ (Baixo Risco)"
        elif score_med >= 70:
            nota_geral = "A (Baixo Risco)"
        elif score_med >= 60:
            nota_geral = "A- (Baixo Risco)"
        elif score_med >= 50:
            nota_geral = "B+ (Médio Risco)"
        elif score_med >= 40:
            nota_geral = "B (Médio Risco)"

        # --- 5. RENTABILIDADE ESTÁVEL ---
        hash_rent = int(hashlib.sha1(bloco.encode("utf-8")).hexdigest(), 16) % 8 + 10
        total_str = f"{total_vol:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        return {
            "volume_total": f"R$ {total_str}",
            "score_medio": nota_geral,
            "prazo_medio": f"{int(prazo_med)} Dias",
            "rentabilidade_alvo": f"{hash_rent}.5% a.a.",
            "empresas": empresas,
        }
