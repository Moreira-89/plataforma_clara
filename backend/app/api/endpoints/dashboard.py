"""
Router dos dashboards.

COMO FUNCIONA:
    1. `GET /dashboard/gestora` e `GET /dashboard/investidor` devolvem KPIs e tabela.
    2. Os handlers vão só orquestrar: ler o BigQuery e chamar `domain/metricas.py`.
    3. Cada uma exige o seu perfil; hoje respondem 501 por falta da fonte dos aportes.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    AcessoNegadoError: Perfil errado para a rota (403).
    HTTPException: 501 depois da checagem de acesso, por enquanto.
"""

from fastapi import APIRouter, Depends

from app.api.dependencias import exigir_perfil
from app.api.erros import nao_implementado
from app.api.schemas.dashboard import DashboardGestora, DashboardInvestidor
from app.domain.perfis import Perfil

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/gestora",
    response_model=DashboardGestora,
    dependencies=[Depends(exigir_perfil(Perfil.GESTORA))],
)
async def dashboard_gestora() -> DashboardGestora:
    """Visão consolidada da gestora."""
    raise nao_implementado("fonte dos aportes e Firebase Auth")


@router.get(
    "/investidor",
    response_model=DashboardInvestidor,
    dependencies=[Depends(exigir_perfil(Perfil.INVESTIDOR))],
)
async def dashboard_investidor() -> DashboardInvestidor:
    """Visão do investidor autenticado."""
    raise nao_implementado("fonte dos aportes e Firebase Auth")
