"""
Estado de filtros e listagem de Blocos de Liquidez.

Herda DashboardState para reaproveitar os blocos já carregados e adiciona os três
filtros da página. Depois da extração do domínio, o computed var só encaminha os
filtros para `domain/metricas.filtrar_blocos` — a regra de filtragem e a montagem
dos cards ficam disponíveis para o endpoint `GET /blocos` da Fase 2, que vai
precisar exatamente da mesma coisa.
"""

import logging
from typing import Any

import reflex as rx

from plataforma_clara.domain import metricas
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

    Os filtros operam em memória sobre os dados já carregados — mudar um filtro não
    consulta o banco de novo.
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
        Aplica os filtros ativos sobre os blocos carregados e monta os cards.

        Returns:
            list[dict[str, Any]]: Cards prontos para o rx.foreach da página.
        """
        cards = metricas.filtrar_blocos(
            self._para_modelos(self.dados_blocos_gestora),
            termo_busca=self.termo_busca,
            filtro_setor=self.filtro_setor,
            filtro_score=self.filtro_score,
        )
        return [card.model_dump() for card in cards]
