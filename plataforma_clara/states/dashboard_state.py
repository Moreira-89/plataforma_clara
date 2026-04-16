import logging
from typing import Any
from typing import List, Dict

import reflex as rx

from plataforma_clara.services.assistente_ia import gerar_insight_relatorio_langchain
from plataforma_clara.services.dashboard_service import buscar_metricas_blocos_liquidez
from plataforma_clara.states.autenticacao_state import AutenticacaoState

logger = logging.getLogger(__name__)


class DashboardState(rx.State):
    """Estado compartilhado pelos dashboards de gestora e investidor."""

    dados_blocos_gestora: List[Dict[str, Any]] = []
    bloco_selecionado_gestora: str = "Todos"
    lista_nomes_blocos: List[str] = ["Todos"]

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

        cpf_logado = AutenticacaoState.documento_usuario_logado

        if not cpf_logado:
            return rx.redirect("/")

        self.dados_blocos = buscar_metricas_blocos_liquidez(cpf_investidor=cpf_logado)

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


    @rx.event
    def carregar_dados_gestora(self):
        """Busca os dados globais e extrai os nomes dos blocos para o menu."""
        from plataforma_clara.services.dashboard_service import buscar_metricas_gerais_gestora
        
        # Opcional: Adicionar a guarda de rota aqui verificando o tipo_usuario_logado
        
        self.dados_blocos_gestora = buscar_metricas_gerais_gestora()
        
        if self.dados_blocos_gestora:
            # Cria a lista de opções do menu dinamicamente baseada no banco
            nomes = [item["bloco_liquidez_setorial"] for item in self.dados_blocos_gestora]
            self.lista_nomes_blocos = ["Todos"] + nomes
            
            # Força o recálculo inicial
            self.set_bloco_selecionado_gestora("Todos")

    @rx.event
    def set_bloco_selecionado_gestora(self, novo_bloco: str):
        """Atualiza os KPIs na tela toda vez que a gestora escolhe um bloco diferente no menu."""
        self.bloco_selecionado_gestora = novo_bloco
        
        if novo_bloco == "Todos":
            dados_filtrados = self.dados_blocos_gestora
        else:
            dados_filtrados = [b for b in self.dados_blocos_gestora if b["bloco_liquidez_setorial"] == novo_bloco]
            
        if dados_filtrados:
            self.total_alocado_geral = sum(item["total_alocado"] for item in dados_filtrados)
            total_scores = sum(item["score_medio_reputacao"] for item in dados_filtrados)
            self.score_medio_geral = round(total_scores / len(dados_filtrados), 2)
            self.quantidade_total_aportes = sum(item["quantidade_aportes"] for item in dados_filtrados)
            
            # Atualiza o gráfico de pizza apenas com os dados filtrados
            self.dados_blocos = dados_filtrados