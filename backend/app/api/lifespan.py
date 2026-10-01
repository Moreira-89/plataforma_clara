"""
Ciclo de vida da aplicação.

Roda uma vez na subida e uma vez no encerramento. É onde entram a configuração de
logging, o Firebase Admin e, quando existir, o cliente do Redis.

COMO FUNCIONA:
    1. Subida — Configura o logging e avisa das integrações sem configuração e
       inicializa o Firebase Admin (sem chamada de rede).
    2. `yield` — A aplicação atende requisições enquanto está parada nesta linha.
    3. Encerramento — O que vier depois do yield roda no shutdown.

Args:
    Nenhum.

Returns:
    None.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.logging import configurar_logging
from app.config.settings import settings
from app.storage.firebase import inicializar_firebase

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

    # Só o nome da integração vai para o log, nunca o valor.
    if not settings.groq_api_key.get_secret_value():
        logger.warning("Groq sem chave configurada: a geração de relatório vai falhar.")
    if not settings.google_application_credentials:
        logger.warning("Sem credencial GCP no ambiente: BigQuery usa as credenciais padrão.")

    await asyncio.to_thread(inicializar_firebase)

    # O cliente do Redis entra aqui.

    yield

    logger.info("Backend encerrando.")
