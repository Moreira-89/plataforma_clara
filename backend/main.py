from fastapi import FastAPI

from app.api.lifespan import lifespan
from app.api.router import router

app = FastAPI(
    title="Plataforma Clara — API",
    description="Transparência e análise de risco para FIDCs.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
