"""
Router de autenticação.

A identidade é do Firebase Auth; o backend só verifica o token e lê as claims.

COMO FUNCIONA:
    1. `POST /auth/login` e `POST /auth/register` são o contrato planejado.
    2. Hoje respondem 501 até o Firebase Auth entrar.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    HTTPException: 501 em todas as rotas, por enquanto.
"""

from fastapi import APIRouter

from app.api.erros import nao_implementado

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login() -> None:
    """Entrada do usuário. Corpo e resposta definidos junto com o Firebase Auth."""
    raise nao_implementado("Firebase Auth")


@router.post("/register")
async def registrar() -> None:
    """Cadastro do usuário. Corpo e resposta definidos junto com o Firebase Auth."""
    raise nao_implementado("Firebase Auth")
