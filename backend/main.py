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