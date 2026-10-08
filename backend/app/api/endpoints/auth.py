"""
Router de autenticação.

O login acontece no navegador, pelo SDK do Firebase, que devolve um ID token; o
backend só o verifica em cada requisição. Por isso não existe `/auth/login`.

COMO FUNCIONA:
    1. `GET /auth/me` devolve o usuário do token.
    2. `POST /auth/register` cria uma conta de investidor (aberta).
    3. `POST /auth/register/gestora` cria uma conta de gestora (só gestora autenticada).
    4. O handler valida no domínio e manda o I/O para `asyncio.to_thread`.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    DocumentoInvalidoError: Documento inválido (422).
    DocumentoJaCadastradoError: Documento já em uso (409).
    EmailJaCadastradoError: E-mail já em uso (409).
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencias import Cadastrador, exigir_perfil, obter_cadastrador, obter_usuario_atual
from app.api.schemas.auth import CadastroRequisicao, CadastroResposta, UsuarioAtual
from app.domain.perfis import Perfil, validar_cadastro

router = APIRouter(prefix="/auth", tags=["auth"])


async def _cadastrar(
    corpo: CadastroRequisicao, perfil: Perfil, cadastrar: Cadastrador
) -> CadastroResposta:
    """Valida no domínio e cria a conta com o perfil dado."""
    dados = validar_cadastro(corpo.nome, corpo.email, corpo.documento, perfil)
    uid = await asyncio.to_thread(cadastrar, dados, corpo.senha.get_secret_value(), perfil)
    return CadastroResposta(uid=uid, perfil=perfil)


@router.get("/me", response_model=UsuarioAtual)
async def quem_sou_eu(
    usuario: Annotated[UsuarioAtual, Depends(obter_usuario_atual)],
) -> UsuarioAtual:
    """Usuário e perfil do token enviado."""
    return usuario


@router.post("/register", response_model=CadastroResposta, status_code=status.HTTP_201_CREATED)
async def registrar_investidor(
    corpo: CadastroRequisicao,
    cadastrar: Annotated[Cadastrador, Depends(obter_cadastrador)],
) -> CadastroResposta:
    """Cadastro de investidor. Aberto, sem token."""
    return await _cadastrar(corpo, Perfil.INVESTIDOR, cadastrar)


@router.post(
    "/register/gestora",
    response_model=CadastroResposta,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_perfil(Perfil.GESTORA))],
)
async def registrar_gestora(
    corpo: CadastroRequisicao,
    cadastrar: Annotated[Cadastrador, Depends(obter_cadastrador)],
) -> CadastroResposta:
    """Cadastro de gestora. Exige token de gestora; o documento precisa ser CNPJ."""
    return await _cadastrar(corpo, Perfil.GESTORA, cadastrar)
