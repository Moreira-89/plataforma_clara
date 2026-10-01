"""
Router dos Blocos de Liquidez.

COMO FUNCIONA:
    1. `GET /blocos` lista as métricas por bloco.
    2. `GET /blocos/{bloco_id}` devolve KPIs e carteira de um bloco.
    3. Hoje respondem 501: dependem da fonte dos aportes.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    HTTPException: 501 em todas as rotas, por enquanto.
"""

from fastapi import APIRouter

from app.api.erros import nao_implementado
from app.api.schemas.contratos import DetalheBloco, MetricaBloco

router = APIRouter(prefix="/blocos", tags=["blocos"])


@router.get("", response_model=list[MetricaBloco])
async def listar_blocos() -> list[MetricaBloco]:
    """Métricas de todos os blocos."""
    raise nao_implementado("fonte dos aportes")


@router.get("/{bloco_id}", response_model=DetalheBloco)
async def detalhar_bloco(bloco_id: str) -> DetalheBloco:
    """Detalhe de um bloco."""
    raise nao_implementado("fonte dos aportes")
