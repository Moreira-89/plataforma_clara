"""
Erros HTTP compartilhados pelos routers.

COMO FUNCIONA:
    1. `nao_implementado` monta o 501 que os endpoints-esqueleto devolvem.
    2. `registrar_handlers` traduz cada `ErroDeNegocio` do domínio num status HTTP,
       para os endpoints e dependências levantarem o erro de domínio sem montar resposta.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.domain import erros

_STATUS_POR_ERRO: dict[type[erros.ErroDeNegocio], int] = {
    erros.DadosIncompletosError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    erros.EmailInvalidoError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    erros.DocumentoInvalidoError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    erros.EmailJaCadastradoError: status.HTTP_409_CONFLICT,
    erros.DocumentoJaCadastradoError: status.HTTP_409_CONFLICT,
    erros.TokenInvalidoError: status.HTTP_401_UNAUTHORIZED,
    erros.PerfilAusenteError: status.HTTP_403_FORBIDDEN,
    erros.AcessoNegadoError: status.HTTP_403_FORBIDDEN,
    erros.AutenticacaoIndisponivelError: status.HTTP_503_SERVICE_UNAVAILABLE,
    erros.BlocoInvalidoError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    erros.EmpresaNaoEncontradaError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    erros.EmpresaJaEmBlocoError: status.HTTP_409_CONFLICT,
    erros.BlocoNaoEncontradoError: status.HTTP_404_NOT_FOUND,
    erros.DadosIndisponiveisError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def nao_implementado(depende_de: str) -> HTTPException:
    """
    Cria o 501 de uma rota que existe no contrato mas ainda não tem implementação.

    Args:
        depende_de (str): O que falta para a rota funcionar.

    Returns:
        HTTPException: Exceção 501 pronta para `raise`.
    """
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Não implementado: depende de {depende_de}.",
    )


def registrar_handlers(app: FastAPI) -> None:
    """
    Liga os erros de negócio ao status HTTP correspondente.

    Args:
        app (FastAPI): A aplicação.
    """

    async def traduzir(_: Request, erro: Exception) -> JSONResponse:
        codigo = _STATUS_POR_ERRO[type(erro)]
        cabecalhos = {"WWW-Authenticate": "Bearer"} if codigo == 401 else None
        return JSONResponse({"detail": str(erro)}, status_code=codigo, headers=cabecalhos)

    for classe in _STATUS_POR_ERRO:
        app.add_exception_handler(classe, traduzir)
