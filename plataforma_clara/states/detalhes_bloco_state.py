"""
Estado de detalhes de um Bloco de Liquidez específico.

Depois da extração do domínio, este state lê o parâmetro da rota, chama
`services/bloco_service.detalhar_bloco` e distribui o resultado nas vars da página.
A consulta foi para o repositório e a formatação para `domain/metricas.py`.
"""

import asyncio
import logging
import urllib.parse
from typing import Any

import reflex as rx

from plataforma_clara.domain.schemas import DetalheBloco
from plataforma_clara.services.bloco_service import detalhar_bloco
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
    Estado da página de detalhes de um bloco de liquidez.

    Herda DashboardState para manter a sessão de usuário e as permissões.
    """

    nome_bloco: str = ""
    volume_total: str = ""
    rentabilidade_alvo: str = ""
    score_medio: str = ""
    prazo_medio: str = ""
    empresas_bloco: list[dict[str, Any]] = []

    # -----------------------------------------------------------------------------
    # MÉTODOS AUXILIARES INTERNOS
    # -----------------------------------------------------------------------------

    def _aplicar_detalhe(self, detalhe: DetalheBloco) -> None:
        """Distribui o detalhe do bloco nas vars que a página renderiza."""
        self.volume_total = detalhe.volume_total
        self.score_medio = detalhe.score_medio
        self.prazo_medio = detalhe.prazo_medio
        self.rentabilidade_alvo = detalhe.rentabilidade_alvo
        self.empresas_bloco = [empresa.model_dump() for empresa in detalhe.empresas]

    # -----------------------------------------------------------------------------
    # EVENTOS PÚBLICOS
    # -----------------------------------------------------------------------------

    @rx.event
    async def carregar_detalhes(self):
        """
        Lê o parâmetro da rota e carrega os dados do bloco.

        COMO FUNCIONA:
            1. Leitura do Parâmetro — `router.page.params` é o único caminho
               suportado para ler parâmetro de rota dinâmica em event handler. O
               Reflex pode devolver o valor como lista, daí o unwrap.
            2. Validação — Sem bloco na URL, a página fica com os valores padrão.
            3. Decodificação — O nome do bloco vem URL-encoded na rota.
            4. Busca em Thread — Consulta bloqueante, fora do event loop.
            5. Atualização do Estado.

        Uma falha de banco é registrada e a página mantém o que já estava na tela,
        em vez de zerar os KPIs — comportamento preservado da versão anterior.
        """
        # --- 1. LEITURA DO PARÂMETRO ---
        bloco_id_bruto = self.router.page.params.get("bloco_id", "")
        bloco_id = (
            bloco_id_bruto[0]
            if isinstance(bloco_id_bruto, list) and bloco_id_bruto
            else bloco_id_bruto
        )

        # --- 2. VALIDAÇÃO ---
        if not bloco_id:
            self.nome_bloco = ""
            self._aplicar_detalhe(DetalheBloco())
            return

        # --- 3. DECODIFICAÇÃO ---
        nome_bloco = urllib.parse.unquote(str(bloco_id))
        self.nome_bloco = nome_bloco

        # --- 4. BUSCA EM THREAD ---
        try:
            detalhe = await asyncio.to_thread(detalhar_bloco, nome_bloco)
        except Exception:
            logger.exception("Erro ao carregar detalhes do bloco: %s", nome_bloco)
            return

        # --- 5. ATUALIZAÇÃO DO ESTADO ---
        self._aplicar_detalhe(detalhe)
