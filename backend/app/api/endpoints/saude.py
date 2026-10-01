"""
Router do healthcheck.

Modelo para os demais routers: um `APIRouter` por recurso, com `tags` próprias.
O `prefix` fica vazio porque a rota é `/health`; os outros usam o do recurso
(`/auth`, `/blocos`, ...). Sem `/api` no prefixo: o proxy do Vite já o remove.

COMO FUNCIONA:
    1. `router` agrupa as rotas do recurso.
    2. O handler só orquestra: monta a resposta e devolve.
    3. O `main.py` acopla o router com `include_router`.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    Nenhum.
"""

from fastapi import APIRouter, Request

from app.api.schemas.saude import RespostaSaude

router = APIRouter(tags=["saude"])


@router.get("/health", response_model=RespostaSaude)
async def verificar_saude(request: Request) -> RespostaSaude:
    """
    Informa que o processo está de pé. Não consulta BigQuery nem outro serviço.

    Args:
        request (Request): Requisição, de onde se lê a versão do app.

    Returns:
        RespostaSaude: Status e versão da API.
    """
    return RespostaSaude(status="ok", versao=request.app.version)
