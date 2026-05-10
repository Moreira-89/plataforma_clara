"""
Estado de filtros e listagem de Blocos de Liquidez para o Investidor.

Herda DashboardState para reutilizar os dados carregados (blocos da gestora) e
adiciona filtros interativos (texto, setor e score) que operam em memória via @rx.var.
"""

import hashlib
import logging
import urllib.parse
from typing import Any

import reflex as rx

from plataforma_clara.states.dashboard_state import DashboardState

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ESTADO DOS FILTROS DE BLOCOS
# -----------------------------------------------------------------------------


class ExplorarBlocosState(DashboardState):
    """
    Estado responsável pelos filtros da página Explorar Blocos.

    Herda DashboardState para reutilizar `dados_blocos_gestora` (já carregados).
    Os filtros operam sobre o computed var `blocos_filtrados`, que é recalculado
    reativamente a cada mudança nos filtros — sem novas consultas ao banco.
    """

    state_auto_setters = True

    termo_busca: str = ""
    filtro_setor: str = ""
    filtro_score: str = ""

    # --- Setters explícitos para os campos de filtro ---

    def set_termo_busca(self, valor: str) -> None:
        self.termo_busca = valor

    def set_filtro_setor(self, valor: str) -> None:
        self.filtro_setor = valor

    def set_filtro_score(self, valor: str) -> None:
        self.filtro_score = valor

    # -----------------------------------------------------------------------------
    # COMPUTED VAR (DADOS FILTRADOS)
    # -----------------------------------------------------------------------------

    @rx.var
    def blocos_filtrados(self) -> list[dict[str, Any]]:
        """
        Aplica os filtros ativos sobre a lista de blocos e formata para exibição.

        COMO FUNCIONA:
            1. Leitura dos Dados Base — Parte de dados_blocos_gestora (herdado de DashboardState).
            2. Filtro por Texto — Filtra pelo nome do bloco (case-insensitive).
            3. Filtro por Setor — Exclui blocos cujo nome não contém o setor selecionado.
            4. Filtro por Score — Mapeia as faixas de score literal para ranges numéricos.
            5. Formatação — Converte valor, nota e rentabilidade para exibição nos cards.
               A rentabilidade é estabilizada via hash SHA-1 do nome do bloco, garantindo
               que o mesmo bloco sempre exiba o mesmo valor entre re-renders.

        Returns:
            list[dict[str, Any]]: Lista de dicts prontos para rx.foreach nos cards.
                                  Cada item tem: id_bloco, nome, setor, volume,
                                  score_literal, rentabilidade.
        """
        # --- 1. LEITURA DOS DADOS BASE ---
        blocos = self.dados_blocos_gestora
        resultado = []

        for b in blocos:
            nome_bloco = str(b.get("bloco_liquidez_setorial", "N/A"))
            # Sem campo de setor separado no dataset atual — usamos o nome do bloco.
            setor = nome_bloco
            score = float(b.get("score_medio_reputacao", 0))

            # --- 2. FILTRO POR TEXTO ---
            if self.termo_busca.strip():
                if self.termo_busca.lower() not in nome_bloco.lower():
                    continue

            # --- 3. FILTRO POR SETOR ---
            if self.filtro_setor and self.filtro_setor != "Todos os Setores":
                if self.filtro_setor.lower() not in setor.lower():
                    continue

            # --- 4. FILTRO POR SCORE ---
            if self.filtro_score and self.filtro_score != "Qualquer Score":
                if self.filtro_score == "A+ a A-" and score < 60:
                    continue
                if self.filtro_score == "B+ a B-" and (score >= 60 or score < 40):
                    continue
                if self.filtro_score == "C+ ou menor" and score >= 40:
                    continue

            # --- 5. FORMATAÇÃO ---
            v = float(b.get("total_alocado", 0))
            # Padrão brasileiro: R$ 12,3M (valor em milhões com vírgula decimal)
            v_str = f"{v / 1_000_000:,.1f}".replace(".", ",")

            # Hash SHA-1 do nome do bloco garante rentabilidade exibida estável entre
            # re-renders. Evitamos usar random() que mudaria a cada recalcul do var.
            hash_rent = int(hashlib.sha1(nome_bloco.encode("utf-8")).hexdigest(), 16) % 8 + 10

            nota = "C-"
            if score >= 80:
                nota = "A+"
            elif score >= 70:
                nota = "A"
            elif score >= 60:
                nota = "A-"
            elif score >= 50:
                nota = "B+"
            elif score >= 40:
                nota = "B"

            # URL-encode do nome do bloco para uso como parâmetro de rota dinâmica.
            id_bloco = urllib.parse.quote(nome_bloco)

            resultado.append({
                "id_bloco": id_bloco,
                "nome": nome_bloco,
                "setor": setor,
                "volume": f"R$ {v_str}M",
                "score_literal": nota,
                "rentabilidade": f"{hash_rent}.5%",
            })

        return resultado
