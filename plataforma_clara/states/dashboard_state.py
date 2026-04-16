import logging
from typing import Any

import reflex as rx

from plataforma_clara.services.assistente_ia import gerar_insight_relatorio_langchain
from plataforma_clara.services.dashboard_service import buscar_metricas_blocos_liquidez

logger = logging.getLogger(__name__)


class DashboardState(rx.State):
    """Estado compartilhado pelos dashboards de gestora e investidor."""

    # Dados brutos vindos do BigQuery
    dados_blocos: list[dict[str, Any]] = []

    # Insights gerados pela IA (Mocks por enquanto)
    insight_ia: str = ""

    # Métricas consolidadas para os Cards de topo
    total_alocado_geral: float = 0.0
    score_medio_geral: float = 0.0
    quantidade_total_aportes: int = 0

    # Mensagem de erro para feedback ao usuário
    mensagem_erro: str = ""

    @rx.event
    def carregar_dados_dashboard(self):
        """
        Evento disparado ao carregar a página (on_load).
        Busca os dados no BigQuery e processa os totais.
        """
        self.mensagem_erro = ""

        self.dados_blocos = buscar_metricas_blocos_liquidez()

        if not self.dados_blocos:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard carregado sem dados.")
            return

        # Calcula métricas globais
        self.total_alocado_geral = sum(
            item.get("total_alocado", 0) for item in self.dados_blocos
        )

        # Média simples dos scores
        total_scores = sum(
            item.get("score_medio_reputacao", 0) for item in self.dados_blocos
        )
        self.score_medio_geral = round(total_scores / len(self.dados_blocos), 2)

        self.quantidade_total_aportes = sum(
            item.get("quantidade_aportes", 0) for item in self.dados_blocos
        )

        # Gera o insight inicial (usando o Mock do LangChain)
        self.insight_ia = gerar_insight_relatorio_langchain(self.dados_blocos[0])

        logger.info(
            "Dashboard carregado: %d blocos, R$ %.2f alocados.",
            len(self.dados_blocos),
            self.total_alocado_geral,
        )

    @rx.var
    def dados_grafico_pizza(self) -> list[dict[str, Any]]:
        """Propriedade computada que formata os dados para o gráfico de pizza."""
        return [
            {"name": item["bloco_liquidez_setorial"], "value": item["total_alocado"]}
            for item in self.dados_blocos
        ]

    @rx.var
    def ranking_empresas_mock(self) -> list[dict[str, Any]]:
        """
        Retorna um ranking simulado para o Dashboard do Investidor.
        No futuro, isso virá de uma query específica de 'Empresas Sacadas'.
        """
        return [
            {"empresa": "Transportes Rápidos LTDA", "score": 92.5, "status": "Excelente"},
            {"empresa": "Indústria Metalúrgica Silva", "score": 88.0, "status": "Bom"},
            {"empresa": "Varejo Alimentos S.A", "score": 75.2, "status": "Regular"},
        ]