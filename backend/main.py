from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.erros import registrar_handlers
from app.api.lifespan import lifespan
from app.api.router import router
from app.config.settings import settings

app = FastAPI(
    title="Plataforma Clara — API",
    description="Transparência e análise de risco para FIDCs.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origens_cors,
    allow_methods=["*"],
    allow_headers=["*"],
)
registrar_handlers(app)
app.include_router(router)
