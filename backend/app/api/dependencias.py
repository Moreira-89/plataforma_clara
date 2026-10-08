"""
Dependências do FastAPI: identidade do usuário e controle de acesso por perfil.

COMO FUNCIONA:
    1. `obter_usuario_atual` extrai o Bearer, verifica o token e monta o `UsuarioAtual`.
    2. `exigir_perfil(...)` fabrica uma dependência que recusa perfis fora da lista.
    3. `obter_verificador_token` e `obter_cadastrador` entregam as funções de I/O; nos
       testes são trocadas com `dependency_overrides`.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    TokenInvalidoError: Header ausente ou token inválido (vira 401).
    PerfilAusenteError: Token sem perfil (vira 403).
    AcessoNegadoError: Perfil sem permissão para a rota (vira 403).
"""

import asyncio
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.schemas.auth import UsuarioAtual
from app.domain.erros import AcessoNegadoError, TokenInvalidoError
from app.domain.perfis import DadosCadastro, Perfil, perfil_de_claims
from app.storage import firebase, usuarios

Verificador = Callable[[str], dict[str, Any]]
Cadastrador = Callable[[DadosCadastro, str, Perfil], str]

# auto_error=False para o 401 sair pelo nosso handler, com o mesmo formato dos demais.
_esquema_bearer = HTTPBearer(auto_error=False)


def obter_verificador_token() -> Verificador:
    """Entrega a função que verifica o ID token."""
    return firebase.verificar_token


def obter_cadastrador() -> Cadastrador:
    """Entrega a função que cria a conta completa."""
    return usuarios.cadastrar_usuario


async def obter_usuario_atual(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema_bearer)],
    verificar: Annotated[Verificador, Depends(obter_verificador_token)],
) -> UsuarioAtual:
    """
    Identifica o usuário a partir do header `Authorization: Bearer <token>`.

    Args:
        credenciais (HTTPAuthorizationCredentials | None): Bearer extraído do header.
        verificar (Verificador): Função que verifica o token.

    Returns:
        UsuarioAtual: uid, perfil e e-mail do token.

    Raises:
        TokenInvalidoError: Sem header, ou token inválido.
        PerfilAusenteError: Token válido sem perfil.
    """
    if credenciais is None:
        raise TokenInvalidoError("Token de acesso ausente.")

    claims = await asyncio.to_thread(verificar, credenciais.credentials)
    return UsuarioAtual(
        uid=claims["uid"],
        perfil=perfil_de_claims(claims),
        email=claims.get("email"),
    )


def exigir_perfil(*perfis: Perfil) -> Callable[..., Any]:
    """
    Cria a dependência que só deixa passar os perfis informados.

    Args:
        *perfis (Perfil): Perfis autorizados.

    Returns:
        Callable: Dependência que devolve o `UsuarioAtual` ou recusa com 403.
    """

    async def dependencia(
        usuario: Annotated[UsuarioAtual, Depends(obter_usuario_atual)],
    ) -> UsuarioAtual:
        if usuario.perfil not in perfis:
            raise AcessoNegadoError("Seu perfil não tem acesso a este recurso.")
        return usuario

    return dependencia
