"""
Junta os routers da API.

COMO FUNCIONA:
    1. Importa o router de cada recurso.
    2. Inclui todos em um `APIRouter` único, que o `main.py` acopla.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` agregado.

Raises:
    Nenhum.
"""

from fastapi import APIRouter

from app.api.endpoints import auth, blocos, dashboard, empresas, relatorios, saude

router = APIRouter()

for modulo in (saude, auth, dashboard, blocos, empresas, relatorios):
    router.include_router(modulo.router)
