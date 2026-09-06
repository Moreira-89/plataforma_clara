"""
Ciclo de vida da aplicação.

Roda uma vez na subida e uma vez no encerramento. É onde entram a configuração de
logging e, quando existirem, os clientes de Firestore e Redis.

COMO FUNCIONA:
    1. Subida — Configura o logging antes de qualquer trabalho.
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
    logger.info("Backend iniciando.")

    # Clientes de Firestore, Redis e Firebase Admin entram aqui.

    yield

    logger.info("Backend encerrando.")
