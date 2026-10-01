"""
Router dos dashboards.

COMO FUNCIONA:
    1. `GET /dashboard/gestora` e `GET /dashboard/investidor` devolvem KPIs e tabela.
    2. Os handlers vão só orquestrar: ler o BigQuery e chamar `domain/metricas.py`.
    3. Hoje respondem 501: faltam a fonte dos aportes e a autenticação.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    HTTPException: 501 em todas as rotas, por enquanto.
"""

from fastapi import APIRouter

from app.api.erros import nao_implementado
from app.api.schemas.dashboard import DashboardGestora, DashboardInvestidor

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/gestora", response_model=DashboardGestora)
async def dashboard_gestora() -> DashboardGestora:
    """Visão consolidada da gestora."""
    raise nao_implementado("fonte dos aportes e Firebase Auth")


@router.get("/investidor", response_model=DashboardInvestidor)
async def dashboard_investidor() -> DashboardInvestidor:
    """Visão do investidor autenticado."""
    raise nao_implementado("fonte dos aportes e Firebase Auth")
