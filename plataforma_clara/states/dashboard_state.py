import logging
from typing import Any

import reflex as rx

from plataforma_clara.services.assistente_ia import gerar_insight_relatorio_langchain
from plataforma_clara.services.dashboard_service import (
    buscar_metricas_blocos_liquidez,
    buscar_metricas_gerais_gestora,
)

logger = logging.getLogger(__name__)


class DashboardState(rx.State):
    """Estado compartilhado pelos dashboards de gestora e investidor."""

    # ── Gestora: dados globais e filtro por bloco ────────────────────────────
    dados_blocos_gestora: list[dict[str, Any]] = []
    bloco_selecionado_gestora: str = "Todos"
    lista_nomes_blocos: list[str] = ["Todos"]

    # ── Dados de exibição (compartilhados pelos KPIs/gráficos) ───────────────
    dados_blocos: list[dict[str, Any]] = []

    # Insights gerados pela IA (Mocks por enquanto)
    insight_ia: str = ""

    # Métricas consolidadas para os Cards de topo
    total_alocado_geral: float = 0.0
    score_medio_geral: float = 0.0
    quantidade_total_aportes: int = 0

    # Mensagem de erro para feedback ao usuário
    mensagem_erro: str = ""

    # ── Helpers internos ─────────────────────────────────────────────────────

    def _calcular_metricas(self, dados: list[dict[str, Any]]) -> None:
        """Recalcula KPIs a partir de uma lista de blocos."""
        if not dados:
            self.total_alocado_geral = 0.0
            self.score_medio_geral = 0.0
            self.quantidade_total_aportes = 0
            return

        self.total_alocado_geral = sum(
            item.get("total_alocado", 0) for item in dados
        )
        total_scores = sum(
            item.get("score_medio_reputacao", 0) for item in dados
        )
        self.score_medio_geral = round(total_scores / len(dados), 2)
        self.quantidade_total_aportes = sum(
            item.get("quantidade_aportes", 0) for item in dados
        )

    # ── Investidor ───────────────────────────────────────────────────────────

    @rx.event
    def carregar_dados_dashboard(self):
        """
        Evento disparado ao carregar o dashboard do investidor.
        Busca dados filtrados pelo documento do investidor logado.
        """
        self.mensagem_erro = ""

        # Acessa o sub-state de autenticação de forma segura via get_state()
        auth = self.get_state(
            # import inline para evitar circular import no module-level
            __import__(
                "plataforma_clara.states.autenticacao_state",
                fromlist=["AutenticacaoState"],
            ).AutenticacaoState
        )
        cpf_logado = auth.documento_usuario_logado

        if not cpf_logado:
            return rx.redirect("/")

        self.dados_blocos = buscar_metricas_blocos_liquidez(cpf_investidor=cpf_logado)

        if not self.dados_blocos:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard investidor carregado sem dados.")
            return

        self._calcular_metricas(self.dados_blocos)

        # Gera o insight inicial (usando o Mock do LangChain)
        self.insight_ia = gerar_insight_relatorio_langchain(self.dados_blocos[0])

        logger.info(
            "Dashboard investidor carregado: %d blocos, R$ %.2f alocados.",
            len(self.dados_blocos),
            self.total_alocado_geral,
        )

    # ── Gestora ──────────────────────────────────────────────────────────────

    @rx.event
    def carregar_dados_gestora(self):
        """Busca os dados globais e extrai os nomes dos blocos para o menu."""
        self.mensagem_erro = ""

        self.dados_blocos_gestora = buscar_metricas_gerais_gestora()

        if not self.dados_blocos_gestora:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard gestora carregado sem dados.")
            return

        # Cria a lista de opções do menu dinamicamente
        nomes = [item["bloco_liquidez_setorial"] for item in self.dados_blocos_gestora]
        self.lista_nomes_blocos = ["Todos"] + nomes

        # Calcula os KPIs com todos os blocos e gera insight
        self._aplicar_filtro_bloco("Todos")

        self.insight_ia = gerar_insight_relatorio_langchain(self.dados_blocos_gestora[0])

        logger.info(
            "Dashboard gestora carregado: %d blocos.",
            len(self.dados_blocos_gestora),
        )

    @rx.event
    def set_bloco_selecionado_gestora(self, novo_bloco: str):
        """Atualiza KPIs quando a gestora escolhe um bloco diferente no menu."""
        self._aplicar_filtro_bloco(novo_bloco)

    def _aplicar_filtro_bloco(self, bloco: str) -> None:
        """Filtra dados da gestora por bloco e recalcula KPIs."""
        self.bloco_selecionado_gestora = bloco

        if bloco == "Todos":
            dados_filtrados = self.dados_blocos_gestora
        else:
            dados_filtrados = [
                b for b in self.dados_blocos_gestora
                if b.get("bloco_liquidez_setorial") == bloco
            ]

        self._calcular_metricas(dados_filtrados)
        # Atualiza o gráfico de pizza com os dados filtrados
        self.dados_blocos = dados_filtrados

    # ── Computed vars ────────────────────────────────────────────────────────

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