"""
Contratos de entrada e saída da autenticação.

COMO FUNCIONA:
    1. `CadastroRequisicao` é o corpo de `POST /auth/register`. A senha é `SecretStr`
       para não aparecer em log nem em `repr`.
    2. `CadastroResposta` confirma a conta criada.
    3. `UsuarioAtual` é o usuário que o token verificado representa.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from pydantic import BaseModel, Field, SecretStr

from app.domain.perfis import Perfil


class CadastroRequisicao(BaseModel):
    """Dados para criar uma conta."""

    nome: str = Field(min_length=1)
    email: str
    senha: SecretStr = Field(min_length=8)
    documento: str = Field(description="CPF ou CNPJ, com ou sem máscara")


class CadastroResposta(BaseModel):
    """Conta criada."""

    uid: str
    perfil: Perfil


class UsuarioAtual(BaseModel):
    """Usuário do token verificado."""

    uid: str
    perfil: Perfil
    email: str | None = None
