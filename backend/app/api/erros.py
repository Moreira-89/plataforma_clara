"""
Erros HTTP compartilhados pelos routers.

COMO FUNCIONA:
    1. `nao_implementado` monta o 501 que os endpoints-esqueleto devolvem.
    2. Cada chamada diz o que a rota espera para sair do esqueleto.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from fastapi import HTTPException, status


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
