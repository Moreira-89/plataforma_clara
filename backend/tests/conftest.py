"""
Fixtures compartilhadas pela suíte de testes da Plataforma Clara.

Cobre só o que atravessa a fronteira de I/O da autenticação: um verificador de token
e um cadastro em memória, ligados ao app por `dependency_overrides`. Nada toca Firebase.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from main import app

from app.api.dependencias import obter_cadastrador, obter_verificador_token
from app.domain.erros import DocumentoJaCadastradoError, EmailJaCadastradoError, TokenInvalidoError
from app.domain.perfis import DadosCadastro, Perfil

# Texto do Bearer -> claims que o verificador falso devolve.
TOKENS = {
    "investidor": {"uid": "u-inv", "email": "inv@exemplo.com", "perfil": "investidor"},
    "gestora": {"uid": "u-ges", "email": "ges@exemplo.com", "perfil": "gestora"},
    "sem-perfil": {"uid": "u-x", "email": "x@exemplo.com"},
}


def cabecalho(token: str) -> dict[str, str]:
    """Header Authorization para o token falso."""
    return {"Authorization": f"Bearer {token}"}


def verificador_falso(token: str) -> dict:
    if token not in TOKENS:
        raise TokenInvalidoError("Token inválido ou expirado.")
    return TOKENS[token]


class CadastroFalso:
    """Imita a unicidade de documento e de e-mail do cadastro real."""

    def __init__(self) -> None:
        self.documentos: dict[str, str] = {}
        self.emails: set[str] = set()
        self.chamadas: list[tuple[DadosCadastro, str, Perfil]] = []

    def __call__(self, dados: DadosCadastro, senha: str, perfil: Perfil) -> str:
        self.chamadas.append((dados, senha, perfil))
        if dados.documento in self.documentos:
            raise DocumentoJaCadastradoError("Documento já cadastrado.")
        if dados.email in self.emails:
            raise EmailJaCadastradoError("E-mail já cadastrado.")
        uid = f"uid-{len(self.documentos) + 1}"
        self.documentos[dados.documento] = uid
        self.emails.add(dados.email)
        return uid


@pytest.fixture
def cadastro() -> CadastroFalso:
    return CadastroFalso()


@pytest.fixture
def client(cadastro: CadastroFalso) -> Iterator[TestClient]:
    app.dependency_overrides[obter_verificador_token] = lambda: verificador_falso
    app.dependency_overrides[obter_cadastrador] = lambda: cadastro
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
