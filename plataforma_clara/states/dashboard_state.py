"""
Estado compartilhado pelos dashboards de Investidor e Gestora.

Centraliza o carregamento de dados, cálculo de KPIs e computed vars utilizados
em ambas as visões. Herda rx.State para participar do sistema de estado reativo
do Reflex — subclasses (DetalhesBlocoState, ExplorarBlocosState) herdam automaticamente.
"""

import asyncio
import logging
from typing import Any

import reflex as rx
from sqlalchemy import func

from plataforma_clara.model.schemas import tb_aporte
from plataforma_clara.services.dashboard_service import (
    buscar_metricas_blocos_liquidez,
    buscar_metricas_gerais_gestora,
    buscar_tabela_aportes_gestora,
)

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ESTADO DO DASHBOARD
# -----------------------------------------------------------------------------


class DashboardState(rx.State):
    """
    Estado base compartilhado pelos dashboards de Investidor e Gestora.

    Mantém os dados de blocos, KPIs agregados e tabelas em memória após carregamento.
    Os computed vars (@rx.var) são recalculados automaticamente quando as vars brutas mudam.
    """

    # Dados da visão da Gestora
    dados_blocos_gestora: list[dict[str, Any]] = []
    patrimonio_total_gestora: float = 0.0
    tabela_aportes_gestora: list[dict[str, Any]] = []

    # Dados da visão do Investidor
    tabela_transparencia_investidor: list[dict[str, Any]] = []
    dados_blocos: list[dict[str, Any]] = []

    # KPIs consolidados (atualizados por _calcular_metricas)
    total_alocado_geral: float = 0.0
    score_medio_geral: float = 0.0
    quantidade_total_aportes: int = 0
    mensagem_erro: str = ""

    # -----------------------------------------------------------------------------
    # MÉTODOS AUXILIARES INTERNOS
    # -----------------------------------------------------------------------------

    @staticmethod
    def _to_float(valor: Any) -> float:
        """Conversão segura de qualquer valor para float. Retorna 0.0 em caso de falha."""
        try:
            return float(valor or 0)
        except (TypeError, ValueError):
            return 0.0

    def _calcular_metricas(self, dados: list[dict[str, Any]]) -> None:
        """
        Atualiza os KPIs consolidados a partir da lista de métricas por bloco.

        Args:
            dados (list[dict]): Lista de dicts retornados por buscar_metricas_*.
                                Cada item deve ter: total_alocado, score_medio_reputacao,
                                quantidade_aportes.
        """
        if not dados:
            self.total_alocado_geral = 0.0
            self.score_medio_geral = 0.0
            self.quantidade_total_aportes = 0
            return

        self.total_alocado_geral = sum(
            self._to_float(item.get("total_alocado")) for item in dados
        )
        total_scores = sum(
            self._to_float(item.get("score_medio_reputacao")) for item in dados
        )
        self.score_medio_geral = round(total_scores / len(dados), 2)
        self.quantidade_total_aportes = sum(
            int(self._to_float(item.get("quantidade_aportes"))) for item in dados
        )

    # -----------------------------------------------------------------------------
    # EVENTOS PÚBLICOS — CARREGAMENTO DE DADOS
    # -----------------------------------------------------------------------------

    @rx.event
    async def carregar_dados_dashboard(self):
        """
        Carrega a visão do Investidor filtrada pelo documento logado.

        COMO FUNCIONA:
            1. Limpeza — Reseta todas as variáveis antes de recarregar.
            2. Recuperação do CPF — Obtém o documento do investidor via get_state().
            3. Busca de Blocos — buscar_metricas_blocos_liquidez em thread separada.
            4. Cálculo de KPIs — _calcular_metricas atualiza total_alocado_geral e score_medio_geral.
            5. Tabela de Transparência — Query ORM com func.avg e func.regexp_replace para
               filtrar CPF com ou sem formatação.
        """
        # --- 1. LIMPEZA ---
        self.mensagem_erro = ""
        self.dados_blocos = []
        self.tabela_transparencia_investidor = []
        self._calcular_metricas([])

        # --- 2. RECUPERAÇÃO DO CPF ---
        auth = await self.get_state(
            __import__(
                "plataforma_clara.states.autenticacao_state",
                fromlist=["AutenticacaoState"],
            ).AutenticacaoState
        )
        cpf_logado = auth.documento_usuario_logado
        if not cpf_logado:
            return rx.redirect("/")

        # --- 3. BUSCA DE BLOCOS ---
        self.dados_blocos = await asyncio.to_thread(
            buscar_metricas_blocos_liquidez, cpf_investidor=cpf_logado
        )
        if not self.dados_blocos:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard investidor carregado sem dados.")
            return

        # --- 4. CÁLCULO DE KPIs ---
        self._calcular_metricas(self.dados_blocos)

        # --- 5. TABELA DE TRANSPARÊNCIA ---
        # Usa func.regexp_replace para normalizar o CPF no banco antes de comparar,
        # garantindo que valores com e sem máscara (123.456.789-00 vs 12345678900)
        # sejam tratados de forma uniforme.
        def fetch_transparencia():
            with rx.session() as session:
                return (
                    session.query(
                        tb_aporte.empresa_sacada_nome,
                        tb_aporte.bloco_liquidez_setorial,
                        func.avg(tb_aporte.score_risco_interno).label("score_medio"),
                        func.sum(tb_aporte.valor_mercado_atual).label("valor_total"),
                    )
                    .filter(
                        func.regexp_replace(
                            tb_aporte.documento_investidor_cpf_cnpj,
                            "[^0-9]",
                            "",
                            "g",
                        )
                        == cpf_logado
                    )
                    .filter(tb_aporte.empresa_sacada_nome.isnot(None))
                    .group_by(
                        tb_aporte.empresa_sacada_nome, tb_aporte.bloco_liquidez_setorial
                    )
                    .order_by(func.avg(tb_aporte.score_risco_interno).desc())
                    .all()
                )

        try:
            registros = await asyncio.to_thread(fetch_transparencia)
            for r in registros:
                valor = self._to_float(r.valor_total)
                valor_str = (
                    f"{valor:,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
                self.tabela_transparencia_investidor.append(
                    {
                        "empresa": r.empresa_sacada_nome,
                        "bloco": r.bloco_liquidez_setorial or "N/A",
                        "score": round(self._to_float(r.score_medio), 2),
                        "valor": f"R$ {valor_str}",
                    }
                )
        except Exception:
            logger.exception("Erro ao buscar tabela de transparência do investidor.")

    @rx.event
    async def carregar_dados_gestora(self):
        """
        Carrega a visão global da carteira para a Gestora.

        COMO FUNCIONA:
            1. Limpeza — Reseta todas as variáveis antes de recarregar.
            2. Busca de Blocos — buscar_metricas_gerais_gestora em thread separada.
            3. Tabela de Aportes — buscar_tabela_aportes_gestora em thread separada.
            4. Cálculo de KPIs — _calcular_metricas atualiza total_alocado_geral.
            5. Patrimônio Total — Query direta com func.sum para o somatório completo.
        """
        # --- 1. LIMPEZA ---
        self.mensagem_erro = ""
        self.dados_blocos_gestora = []
        self.dados_blocos = []
        self.tabela_aportes_gestora = []
        self.patrimonio_total_gestora = 0.0
        self._calcular_metricas([])

        # --- 2. BUSCA DE BLOCOS ---
        self.dados_blocos_gestora = await asyncio.to_thread(buscar_metricas_gerais_gestora)
        if not self.dados_blocos_gestora:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard gestora carregado sem dados.")
            return

        # --- 3. TABELA DE APORTES ---
        self.tabela_aportes_gestora = await asyncio.to_thread(buscar_tabela_aportes_gestora)
        self.dados_blocos = self.dados_blocos_gestora

        # --- 4. CÁLCULO DE KPIs ---
        self._calcular_metricas(self.dados_blocos_gestora)

        # --- 5. PATRIMÔNIO TOTAL ---
        def fetch_patrimonio():
            with rx.session() as session:
                return session.query(func.sum(tb_aporte.valor_mercado_atual)).scalar()

        try:
            total = await asyncio.to_thread(fetch_patrimonio)
            self.patrimonio_total_gestora = self._to_float(total)
        except Exception:
            logger.exception("Erro ao buscar patrimônio total da gestora.")

    # -----------------------------------------------------------------------------
    # COMPUTED VARS — FORMATAÇÃO E DERIVAÇÕES
    # -----------------------------------------------------------------------------

    @rx.var
    def dados_grafico_pizza(self) -> list[dict[str, Any]]:
        """Formata os dados de blocos para gráfico de pizza (em milhões de R$)."""
        return [
            {
                "name": item.get("bloco_liquidez_setorial", "N/A"),
                "value": round(self._to_float(item.get("total_alocado")) / 1_000_000, 2),
            }
            for item in self.dados_blocos
        ]

    @rx.var
    def patrimonio_total_investidor(self) -> str:
        """Formata o patrimônio total do investidor no padrão brasileiro (R$ X.XXX.XXX,XX)."""
        texto = f"{self.total_alocado_geral:,.2f}"
        return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def alocacao_blocos_investidor(self) -> list[dict[str, Any]]:
        """Formata dados de blocos do investidor para gráfico de alocação."""
        return [
            {
                "name": item.get("bloco_liquidez_setorial", "N/A"),
                "value": round(self._to_float(item.get("total_alocado")) / 1_000_000, 2),
            }
            for item in self.dados_blocos
        ]

    @rx.var
    def patrimonio_total_gestora_formatado(self) -> str:
        """Formata o patrimônio total sob gestão no padrão brasileiro."""
        texto = f"{self.patrimonio_total_gestora:,.2f}"
        return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def qtd_blocos_ativos(self) -> str:
        """Retorna a quantidade de blocos ativos formatada (singular/plural)."""
        qtd = len(self.dados_blocos_gestora)
        return f"{qtd} Blocos" if qtd != 1 else "1 Bloco"

    @rx.var
    def classificacao_risco_medio(self) -> str:
        """Traduz o score médio numérico para uma classificação literal de risco."""
        if not self.score_medio_geral:
            return "N/A"
        s = self.score_medio_geral
        if s >= 80:
            return "Baixo (A+)"
        if s >= 70:
            return "Baixo (A)"
        if s >= 60:
            return "Moderado (A-)"
        if s >= 50:
            return "Médio (B+)"
        if s >= 40:
            return "Alto (B)"
        return "Crítico (C-)"

    @rx.var
    def inadimplencia_projetada(self) -> str:
        """Calcula o percentual de blocos com score < 50 (alto risco de inadimplência)."""
        if not self.dados_blocos_gestora:
            return "0.0%"
        total = len(self.dados_blocos_gestora)
        baixos = sum(
            1
            for b in self.dados_blocos_gestora
            if self._to_float(b.get("score_medio_reputacao")) < 50
        )
        return f"{round((baixos / total) * 100, 1)}%"

    @rx.var
    def dados_evolucao_aum(self) -> list[dict[str, Any]]:
        """
        Projeta a evolução do AUM nos últimos 6 meses usando fatores estáticos.
        Os fatores simulam crescimento progressivo até o valor atual (100%).
        """
        meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"]
        fatores = [0.83, 0.87, 0.91, 0.95, 0.98, 1.0]
        total = self.patrimonio_total_gestora
        return [
            {"name": mes, "volume": round((total * fator) / 1_000_000, 2)}
            for mes, fator in zip(meses, fatores, strict=False)
        ]

    @rx.var
    def dados_distribuicao_aportes(self) -> list[dict[str, Any]]:
        """Retorna os top 5 blocos por volume alocado para o gráfico de distribuição."""
        return [
            {
                "name": b.get("bloco_liquidez_setorial", "N/A"),
                "alocado": round(self._to_float(b.get("total_alocado")) / 1_000_000, 2),
            }
            for b in self.dados_blocos_gestora[:5]
        ]

    @rx.var
    def dados_rendimento_projetado(self) -> list[dict[str, Any]]:
        """
        Projeta o rendimento esperado para os próximos 6 meses com taxa de 1% a.m.
        Retorna o rendimento acumulado incremental em relação ao total atual.
        """
        meses = ["Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        base = self.total_alocado_geral
        dados: list[dict[str, Any]] = []
        for mes in meses:
            base *= 1.01  # Aplica 1% ao mês de forma composta
            dados.append({
                "name": mes,
                "rendimento": round((base - self.total_alocado_geral) / 1_000_000, 2),
            })
        return dados
