"""
Estado compartilhado pelos dashboards de Investidor e Gestora.

Depois da extração do domínio, este state guarda dados e delega cálculo. Os
computed vars continuam existindo porque é assim que o Reflex reage a mudanças,
mas o corpo de cada um é uma chamada para `domain/metricas.py` ou
`domain/projecoes.py` — nenhuma regra de negócio nasce aqui.

As vars continuam sendo `list[dict]` de propósito: é o formato que os componentes
das páginas indexam (`item["empresa"]`). A conversão DTO → dict acontece na
fronteira, em `_como_dicts`.
"""

import asyncio
import logging
from typing import Any

import reflex as rx

from plataforma_clara.domain import formatacao, metricas, projecoes, risco
from plataforma_clara.domain.schemas import MetricaBloco
from plataforma_clara.services.dashboard_service import (
    buscar_metricas_blocos_liquidez,
    buscar_metricas_gerais_gestora,
    buscar_patrimonio_total,
    buscar_tabela_aportes_gestora,
    buscar_tabela_transparencia_investidor,
)
from plataforma_clara.states.autenticacao_state import AutenticacaoState

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)


def _como_dicts(modelos: list[Any]) -> list[dict[str, Any]]:
    """Converte uma lista de DTOs no formato que os componentes do Reflex indexam."""
    return [modelo.model_dump() for modelo in modelos]


# -----------------------------------------------------------------------------
# ESTADO DO DASHBOARD
# -----------------------------------------------------------------------------


class DashboardState(rx.State):
    """
    Estado base compartilhado pelos dashboards de Investidor e Gestora.

    Mantém os dados de blocos, KPIs agregados e tabelas em memória após o
    carregamento. Subclasses (DetalhesBlocoState, ExplorarBlocosState) herdam tudo.
    """

    # Dados da visão da Gestora
    dados_blocos_gestora: list[dict[str, Any]] = []
    patrimonio_total_gestora: float = 0.0
    tabela_aportes_gestora: list[dict[str, Any]] = []

    # Dados da visão do Investidor
    tabela_transparencia_investidor: list[dict[str, Any]] = []
    dados_blocos: list[dict[str, Any]] = []

    # KPIs consolidados (atualizados por _aplicar_kpis)
    total_alocado_geral: float = 0.0
    score_medio_geral: float = 0.0
    quantidade_total_aportes: int = 0
    mensagem_erro: str = ""

    # -----------------------------------------------------------------------------
    # MÉTODOS AUXILIARES INTERNOS
    # -----------------------------------------------------------------------------

    @staticmethod
    def _para_modelos(blocos: list[dict[str, Any]]) -> list[MetricaBloco]:
        """Reconstrói os DTOs a partir dos dicts guardados no estado."""
        return [MetricaBloco.model_validate(bloco) for bloco in blocos]

    def _aplicar_kpis(self, blocos: list[MetricaBloco]) -> None:
        """
        Recalcula os KPIs consolidados e os grava nas vars do estado.

        Args:
            blocos (list[MetricaBloco]): Métricas por bloco. Lista vazia zera tudo.
        """
        kpis = metricas.consolidar_kpis(blocos)
        self.total_alocado_geral = kpis.total_alocado
        self.score_medio_geral = kpis.score_medio
        self.quantidade_total_aportes = kpis.quantidade_aportes

    # -----------------------------------------------------------------------------
    # EVENTOS PÚBLICOS — CARREGAMENTO DE DADOS
    # -----------------------------------------------------------------------------

    @rx.event
    async def carregar_dados_dashboard(self):
        """
        Carrega a visão do Investidor, filtrada pelo documento logado.

        COMO FUNCIONA:
            1. Limpeza — Reseta as variáveis antes de recarregar, para que uma
               falha não deixe dados do investidor anterior na tela.
            2. Recuperação do Documento — Sem sessão ativa, volta para a home.
            3. Busca dos Blocos — Em thread separada; o serviço cuida do cache.
            4. Cálculo de KPIs.
            5. Tabela de Transparência — Em quais empresas o dinheiro foi aplicado.
        """
        # --- 1. LIMPEZA ---
        self.mensagem_erro = ""
        self.dados_blocos = []
        self.tabela_transparencia_investidor = []
        self._aplicar_kpis([])

        # --- 2. RECUPERAÇÃO DO DOCUMENTO ---
        autenticacao = await self.get_state(AutenticacaoState)
        documento = autenticacao.documento_usuario_logado
        if not documento:
            return rx.redirect("/")

        # --- 3. BUSCA DOS BLOCOS ---
        blocos = await asyncio.to_thread(
            buscar_metricas_blocos_liquidez, documento_investidor=documento
        )
        self.dados_blocos = _como_dicts(blocos)

        if not blocos:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard investidor carregado sem dados.")
            return

        # --- 4. CÁLCULO DE KPIs ---
        self._aplicar_kpis(blocos)

        # --- 5. TABELA DE TRANSPARÊNCIA ---
        transparencia = await asyncio.to_thread(
            buscar_tabela_transparencia_investidor, documento_investidor=documento
        )
        self.tabela_transparencia_investidor = _como_dicts(transparencia)

    @rx.event
    async def carregar_dados_gestora(self):
        """
        Carrega a visão global da carteira para a Gestora.

        COMO FUNCIONA:
            1. Limpeza — Reseta as variáveis antes de recarregar.
            2. Busca dos Blocos — Agregação de toda a base, sem filtro.
            3. Tabela de Empresas — Ranking das empresas sacadas.
            4. Cálculo de KPIs.
            5. Patrimônio Total — Soma direta, independente da agregação por bloco.
        """
        # --- 1. LIMPEZA ---
        self.mensagem_erro = ""
        self.dados_blocos_gestora = []
        self.dados_blocos = []
        self.tabela_aportes_gestora = []
        self.patrimonio_total_gestora = 0.0
        self._aplicar_kpis([])

        # --- 2. BUSCA DOS BLOCOS ---
        blocos = await asyncio.to_thread(buscar_metricas_gerais_gestora)
        if not blocos:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard gestora carregado sem dados.")
            return

        self.dados_blocos_gestora = _como_dicts(blocos)
        # A visão da gestora alimenta os mesmos gráficos do investidor, que leem
        # `dados_blocos` — daí a duplicação deliberada.
        self.dados_blocos = self.dados_blocos_gestora

        # --- 3. TABELA DE EMPRESAS ---
        tabela = await asyncio.to_thread(buscar_tabela_aportes_gestora)
        self.tabela_aportes_gestora = _como_dicts(tabela)

        # --- 4. CÁLCULO DE KPIs ---
        self._aplicar_kpis(blocos)

        # --- 5. PATRIMÔNIO TOTAL ---
        self.patrimonio_total_gestora = await asyncio.to_thread(buscar_patrimonio_total)

    # -----------------------------------------------------------------------------
    # COMPUTED VARS — DERIVAÇÕES PARA A TELA
    # -----------------------------------------------------------------------------

    @rx.var
    def dados_grafico_pizza(self) -> list[dict[str, Any]]:
        """Alocação por bloco, em milhões de reais, para o gráfico de pizza."""
        return metricas.serie_alocacao_por_bloco(self._para_modelos(self.dados_blocos))

    @rx.var
    def alocacao_blocos_investidor(self) -> list[dict[str, Any]]:
        """Mesma série da pizza, consumida pelo gráfico de alocação do investidor."""
        return metricas.serie_alocacao_por_bloco(self._para_modelos(self.dados_blocos))

    @rx.var
    def patrimonio_total_investidor(self) -> str:
        """Patrimônio do investidor formatado em reais."""
        return formatacao.formatar_moeda(self.total_alocado_geral)

    @rx.var
    def patrimonio_total_gestora_formatado(self) -> str:
        """Patrimônio sob gestão formatado em reais."""
        return formatacao.formatar_moeda(self.patrimonio_total_gestora)

    @rx.var
    def qtd_blocos_ativos(self) -> str:
        """Quantidade de blocos ativos, com concordância de número."""
        return metricas.descrever_quantidade_blocos(self._para_modelos(self.dados_blocos_gestora))

    @rx.var
    def classificacao_risco_medio(self) -> str:
        """Score médio traduzido em classificação literal de risco."""
        return risco.classificar_nivel_com_nota(self.score_medio_geral)

    @rx.var
    def inadimplencia_projetada(self) -> str:
        """Percentual de blocos com score abaixo do corte de inadimplência."""
        return metricas.percentual_blocos_em_risco(self._para_modelos(self.dados_blocos_gestora))

    @rx.var
    def dados_evolucao_aum(self) -> list[dict[str, Any]]:
        """Série SIMULADA de evolução do patrimônio — ver `domain/projecoes.py`."""
        return projecoes.evolucao_aum_simulada(self.patrimonio_total_gestora)

    @rx.var
    def dados_distribuicao_aportes(self) -> list[dict[str, Any]]:
        """Os cinco maiores blocos por volume alocado."""
        return metricas.serie_distribuicao_aportes(self._para_modelos(self.dados_blocos_gestora))

    @rx.var
    def dados_rendimento_projetado(self) -> list[dict[str, Any]]:
        """Série SIMULADA de rendimento futuro — ver `domain/projecoes.py`."""
        return projecoes.rendimento_projetado_simulado(self.total_alocado_geral)
