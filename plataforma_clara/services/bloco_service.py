"""
Serviço de consulta de um Bloco de Liquidez específico.

Extraído de `DetalhesBlocoState._buscar_dados_bloco_bq`, que apesar do nome
consultava o PostgreSQL, não o BigQuery. A consulta foi para o repositório e a
formatação para `domain/metricas.py`; aqui sobrou a orquestração.

Diferente das funções de `dashboard_service`, esta PROPAGA a exceção em vez de
devolver vazio — é o comportamento que a página de detalhes já tinha, onde uma
falha preserva na tela os dados carregados antes em vez de zerá-los.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlmodel import Session

from plataforma_clara.domain import metricas
from plataforma_clara.domain.schemas import DetalheBloco
from plataforma_clara.infra.db import sessao as sessao_padrao
from plataforma_clara.infra.repositorios.aporte import AporteRepositorio

logger = logging.getLogger(__name__)

FabricaDeSessao = Callable[[], AbstractContextManager[Session]]


def detalhar_bloco(
    nome_bloco: str,
    *,
    sessao_factory: FabricaDeSessao = sessao_padrao,
) -> DetalheBloco:
    """
    Monta os KPIs e a carteira de empresas de um Bloco de Liquidez.

    Args:
        nome_bloco (str): Nome exato do bloco, já decodificado da URL.
        sessao_factory (FabricaDeSessao): Fábrica de sessão de banco.

    Returns:
        DetalheBloco: KPIs formatados e empresas financiadas. Um bloco sem aportes
                      devolve o detalhe vazio (volume zerado, KPIs 'N/A').

    Raises:
        Exception: Qualquer falha de banco sobe para o chamador.
    """
    with sessao_factory() as sessao:
        empresas = AporteRepositorio(sessao).empresas_do_bloco(nome_bloco)

    logger.info("Bloco '%s' detalhado: %d empresas.", nome_bloco, len(empresas))
    return metricas.montar_detalhe_bloco(nome_bloco, empresas)
