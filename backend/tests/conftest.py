"""
Fixtures compartilhadas pela suíte de testes da Plataforma Clara.

Cobre só o que atravessa a fronteira de I/O da autenticação: um verificador de token
e um cadastro em memória, ligados ao app por `dependency_overrides`. Nada toca Firebase.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from main import app

from app.api.dependencias import (
    obter_buscador_de_bloco,
    obter_buscador_de_empresas,
    obter_cadastrador,
    obter_criador_de_bloco,
    obter_listador_de_blocos,
    obter_verificador_token,
)
from app.domain.blocos import (
    BlocoDetalhado,
    BlocoListado,
    BlocoValidado,
    EmpresaCatalogo,
    EmpresaDoBlocoDetalhada,
)
from app.domain.erros import (
    BlocoNaoEncontradoError,
    DocumentoJaCadastradoError,
    EmailJaCadastradoError,
    TokenInvalidoError,
)
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


EMPRESA_A = EmpresaCatalogo("e1", "Móveis Alfa", "Alfa Móveis Ltda", "11222333000181", "Varejo")
EMPRESA_B = EmpresaCatalogo(
    "e2", "Brinquedos Beta", "Beta Brinquedos SA", "11444777000161", "Varejo"
)


class CatalogoFalso:
    """Imita a busca de empresas, guardando o que foi pedido."""

    def __init__(self) -> None:
        self.buscas: list[str] = []
        self.resultado = [EMPRESA_A, EMPRESA_B]
        self.erro: Exception | None = None

    def __call__(self, busca: str) -> list[EmpresaCatalogo]:
        self.buscas.append(busca)
        if self.erro:
            raise self.erro
        return self.resultado


class CriadorDeBlocoFalso:
    """Imita a gravação do bloco, guardando o que seria gravado."""

    def __init__(self) -> None:
        self.criados: list[tuple[BlocoValidado, str]] = []
        self.erro: Exception | None = None

    def __call__(self, bloco: BlocoValidado, uid: str) -> None:
        if self.erro:
            raise self.erro
        self.criados.append((bloco, uid))


BLOCO_A = BlocoListado(
    id_bloco="b1",
    codigo_identificacao="BLOCO_SAFIRA_1",
    etiqueta="Safira",
    capital_total=Decimal("1000000.00"),
    data_criacao=date(2026, 10, 9),
    data_vencimento=date(2030, 1, 1),
    responsavel_tecnico="Lucas",
    observacao=None,
    quantidade_empresas=2,
)


class LeituraDeBlocosFalsa:
    """Imita a leitura de blocos: uma lista fixa e um detalhe por id."""

    def __init__(self) -> None:
        self.blocos = [BLOCO_A]
        self.erro: Exception | None = None

    def listar(self) -> list[BlocoListado]:
        if self.erro:
            raise self.erro
        return self.blocos

    def buscar(self, id_bloco: str) -> BlocoDetalhado:
        if self.erro:
            raise self.erro
        if id_bloco != BLOCO_A.id_bloco:
            raise BlocoNaoEncontradoError("Bloco não encontrado.")
        return BlocoDetalhado(
            bloco=BLOCO_A,
            empresas=(
                EmpresaDoBlocoDetalhada(
                    "e2",
                    "11444777000161",
                    Decimal("950000.00"),
                    Decimal("95.00"),
                    "Brinquedos Beta",
                    "Varejo",
                ),
                EmpresaDoBlocoDetalhada(
                    "e1", "11222333000181", Decimal("50000.00"), Decimal("5.00"), None, None
                ),
            ),
        )


@pytest.fixture
def leitura_de_blocos() -> LeituraDeBlocosFalsa:
    return LeituraDeBlocosFalsa()


@pytest.fixture
def cadastro() -> CadastroFalso:
    return CadastroFalso()


@pytest.fixture
def catalogo() -> CatalogoFalso:
    return CatalogoFalso()


@pytest.fixture
def criador_de_bloco() -> CriadorDeBlocoFalso:
    return CriadorDeBlocoFalso()


@pytest.fixture
def client(
    cadastro: CadastroFalso,
    catalogo: CatalogoFalso,
    criador_de_bloco: CriadorDeBlocoFalso,
    leitura_de_blocos: LeituraDeBlocosFalsa,
) -> Iterator[TestClient]:
    app.dependency_overrides[obter_verificador_token] = lambda: verificador_falso
    app.dependency_overrides[obter_cadastrador] = lambda: cadastro
    app.dependency_overrides[obter_buscador_de_empresas] = lambda: catalogo
    app.dependency_overrides[obter_criador_de_bloco] = lambda: criador_de_bloco
    app.dependency_overrides[obter_listador_de_blocos] = lambda: leitura_de_blocos.listar
    app.dependency_overrides[obter_buscador_de_bloco] = lambda: leitura_de_blocos.buscar
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
