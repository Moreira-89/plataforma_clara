"""
Router dos relatórios em PDF por IA.

COMO FUNCIONA:
    1. `POST /relatorios` pede a geração; `GET /relatorios/{id}` consulta o estado.
    2. A geração vai chamar `agents.relatorio`, sempre via `asyncio.to_thread`.
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
from app.api.schemas.relatorio import RelatorioStatus

router = APIRouter(prefix="/relatorios", tags=["relatorios"])


@router.post("", response_model=RelatorioStatus)
async def pedir_relatorio() -> RelatorioStatus:
    """Pede o relatório consolidado do investidor autenticado."""
    raise nao_implementado("fonte dos aportes e Firebase Auth")


@router.get("/{relatorio_id}", response_model=RelatorioStatus)
async def consultar_relatorio(relatorio_id: str) -> RelatorioStatus:
    """Estado de um relatório pedido."""
    raise nao_implementado("fonte dos aportes e Firebase Auth")
