"""
Entry point do backend da Plataforma Clara.

Cria a aplicação FastAPI, configura o lifespan e o CORS. Os routers entram aqui
conforme forem escritos em `app/api/` — este arquivo não deve ganhar regra de
negócio nenhuma, só montagem.

COMO FUNCIONA:
    1. Lifespan — Roda uma vez na subida e uma vez no encerramento. É onde entram
       a configuração de logging e, quando existirem, os clientes de Firestore e
       Redis: abrir conexão por requisição é desperdício, e fechá-la no shutdown
       evita conexão pendurada quando o Railway derruba o container.
    2. CORS — O frontend é um serviço separado, em outro domínio. Sem isto o
       browser bloqueia a chamada antes de ela sair.
    3. Rotas — `/health` responde de imediato, para o healthcheck da hospedagem.

Args:
    Nenhum.

Returns:
    FastAPI: a aplicação, servida pelo uvicorn.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.lifespan import lifespan
from app.config.settings import settings

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Plataforma Clara — API",
    description="Transparência e análise de risco para FIDCs.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origens,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["infra"])
async def health() -> dict[str, str]:
    """
    Diz que o processo está de pé.

    Não toca em banco nem em serviço externo de propósito: é o healthcheck da
    hospedagem, e precisa responder mesmo com uma dependência fora do ar. A
    verificação de dependências é papel de um `/ready` separado.

    Returns:
        dict[str, str]: Status e ambiente.
    """
    return {"status": "ok", "ambiente": settings.ambiente}


# OS ROUTERS ENTRAM AQUI conforme forem escritos:
#     app.include_router(aportes.router, prefix="/aportes", tags=["aportes"])
