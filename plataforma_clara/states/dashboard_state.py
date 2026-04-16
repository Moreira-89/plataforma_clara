import reflex as rx
from typing import List, Dict, Any
from plataforma_clara.services.dashboard_service import buscar_metricas_blocos_liquidez
from plataforma_clara.services.assistente_ia import gerar_insight_relatorio_langchain
from plataforma_clara.states.autenticacao_state import AutenticacaoState

class DashboardState(rx.State):
    # Dados brutos vindos do BigQuery
    dados_blocos: List[Dict[str, Any]] = []
    
    # Insights gerados pela IA (Mocks por enquanto)
    insight_ia: str = ""
    
    # Métricas consolidadas para os Cards de topo
    total_alocado_geral: float = 0.0
    score_medio_geral: float = 0.0
    quantidade_total_aportes: int = 0

    @rx.event
    def carregar_dados_dashboard(self):
        """
        Evento disparado ao carregar a página (on_load).
        Busca os dados no BigQuery e processa os totais.
        """
        # 1. Chama o serviço que criamos anteriormente
        self.dados_blocos = buscar_metricas_blocos_liquidez()
        
        # 2. Calcula métricas globais para a Gestora
        if self.dados_blocos:
            self.total_alocado_geral = sum(item["total_alocado"] for item in self.dados_blocos)
            
            # Média ponderada simples dos scores
            total_scores = sum(item["score_medio_reputacao"] for item in self.dados_blocos)
            self.score_medio_geral = round(total_scores / len(self.dados_blocos), 2)
            
            self.quantidade_total_aportes = sum(item["quantidade_aportes"] for item in self.dados_blocos)
            
            # 3. Gera o insight inicial (usando o Mock do LangChain)
            # Passamos o primeiro bloco como exemplo para a IA analisar
            self.insight_ia = gerar_insight_relatorio_langchain(self.dados_blocos[0])
        else:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."

    @rx.var
    def dados_grafico_pizza(self) -> List[Dict[str, Any]]:
        """
        Propriedade computada que formata os dados para o componente de gráfico do Reflex.
        """
        return [
            {"name": item["bloco_liquidez_setorial"], "value": item["total_alocado"]}
            for item in self.dados_blocos
        ]

    @rx.var
    def ranking_empresas_mock(self) -> List[Dict[str, Any]]:
        """
        Retorna um ranking simulado para o Dashboard do Investidor.
        No futuro, isso virá de uma query específica de 'Empresas Sacadas'.
        """
        return [
            {"empresa": "Transportes Rápidos LTDA", "score": 92.5, "status": "Excelente"},
            {"empresa": "Indústria Metalúrgica Silva", "score": 88.0, "status": "Bom"},
            {"empresa": "Varejo Alimentos S.A", "score": 75.2, "status": "Regular"},
        ]