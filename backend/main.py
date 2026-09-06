"""
Entry point do backend da Plataforma Clara.

Cria a aplicação FastAPI e monta o lifespan. Os routers entram aqui conforme forem
escritos em `app/api/` — este arquivo não deve ganhar regra de negócio.

COMO FUNCIONA:
    1. Lifespan — Definido em `app/api/lifespan.py`.
    2. Rotas — `/health` responde de imediato, para o healthcheck da hospedagem.

Args:
    Nenhum.

Returns:
    FastAPI: a aplicação, servida pelo uvicorn.
"""

import logging

from fastapi import FastAPI

from app.api.lifespan import lifespan

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Plataforma Clara — API",
    description="Transparência e análise de risco para FIDCs.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["infra"])
async def health() -> dict[str, str]:
    """
    Diz que o processo está de pé.

    Não toca em serviço externo de propósito: precisa responder mesmo com uma
    dependência fora do ar.

    Returns:
        dict[str, str]: Status da aplicação.
    """
    return {"status": "ok"}


# Routers entram aqui.
