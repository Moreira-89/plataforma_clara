"""
Ciclo de vida da aplicação.

Roda uma vez na subida e uma vez no encerramento. É onde entram a configuração de
logging e, quando existirem, os clientes de Firestore e Redis: abrir conexão por
requisição é desperdício, e fechá-la no shutdown evita conexão pendurada quando o
Railway derruba o container.

COMO FUNCIONA:
    1. Subida — Configura o logging antes de qualquer trabalho, senão os logs dos
       módulos já importados caem na configuração padrão e somem do stdout.
    2. `yield` — A aplicação atende requisições enquanto está parada nesta linha.
    3. Encerramento — O que vier depois do yield roda no shutdown.

Args:
    Nenhum.

Returns:
    None.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.logging import configurar_logging
from app.config.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Prepara e encerra os recursos de processo da aplicação.

    Args:
        app (FastAPI): A aplicação, disponível para guardar clientes em `app.state`.

    Yields:
        None: Enquanto a aplicação está no ar.
    """
    configurar_logging()
    logger.info("Backend iniciando (ambiente: %s).", settings.ambiente)

    # A INSTANCIAR AQUI, quando implementarmos: cliente do Firestore, cliente do
    # Redis e o app do Firebase Admin. Todos guardados em `app.state` e fechados
    # depois do yield.

    yield

    logger.info("Backend encerrando.")
