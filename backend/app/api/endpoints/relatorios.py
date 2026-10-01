"""
Router dos relatórios em PDF por IA.

COMO FUNCIONA:
    1. `POST /relatorios` pede a geração; `GET /relatorios/{id}` consulta o estado.
    2. A geração vai chamar `agents.relatorio`, sempre via `asyncio.to_thread`.
    3. Só o investidor acessa; hoje respondem 501 por falta da fonte dos aportes.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    AcessoNegadoError: Perfil diferente de investidor (403).
    HTTPException: 501 depois da checagem de acesso, por enquanto.
"""

from fastapi import APIRouter, Depends

from app.api.dependencias import exigir_perfil
from app.api.erros import nao_implementado
from app.api.schemas.relatorio import RelatorioStatus
from app.domain.perfis import Perfil

router = APIRouter(
    prefix="/relatorios",
    tags=["relatorios"],
    dependencies=[Depends(exigir_perfil(Perfil.INVESTIDOR))],
)


@router.post("", response_model=RelatorioStatus)
async def pedir_relatorio() -> RelatorioStatus:
    """Pede o relatório consolidado do investidor autenticado."""
    raise nao_implementado("fonte dos aportes e Firebase Auth")


@router.get("/{relatorio_id}", response_model=RelatorioStatus)
async def consultar_relatorio(relatorio_id: str) -> RelatorioStatus:
    """Estado de um relatório pedido."""
    raise nao_implementado("fonte dos aportes e Firebase Auth")
