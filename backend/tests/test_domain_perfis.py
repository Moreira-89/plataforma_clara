"""
Testes de `domain/perfis.py`: leitura do perfil nas claims e validação de cadastro.

Nenhum destes testes precisa de banco ou de rede.
"""

import pytest

from app.domain.erros import (
    DadosIncompletosError,
    DocumentoInvalidoError,
    EmailInvalidoError,
    PerfilAusenteError,
)
from app.domain.perfis import Perfil, perfil_de_claims, validar_cadastro

CPF = "123.456.789-09"
CNPJ = "11.222.333/0001-81"


@pytest.mark.parametrize(
    ("claims", "esperado"),
    [({"perfil": "investidor"}, Perfil.INVESTIDOR), ({"perfil": "gestora"}, Perfil.GESTORA)],
)
def test_perfil_de_claims_valido(claims, esperado):
    assert perfil_de_claims(claims) is esperado


@pytest.mark.parametrize("claims", [{}, {"perfil": None}, {"perfil": ""}, {"perfil": "admin"}])
def test_perfil_de_claims_ausente_ou_desconhecido(claims):
    with pytest.raises(PerfilAusenteError):
        perfil_de_claims(claims)


def test_cadastro_de_investidor_com_cpf_normaliza_os_dados():
    dados = validar_cadastro("  Ana  ", " ANA@Exemplo.com ", CPF, Perfil.INVESTIDOR)

    assert dados.nome == "Ana"
    assert dados.email == "ana@exemplo.com"
    assert dados.documento == "12345678909"
    assert dados.tipo_documento == "CPF"


def test_cadastro_de_investidor_aceita_cnpj():
    assert (
        validar_cadastro("Fundo", "f@exemplo.com", CNPJ, Perfil.INVESTIDOR).tipo_documento == "CNPJ"
    )


def test_cadastro_de_gestora_aceita_cnpj():
    assert (
        validar_cadastro("Núclea", "n@exemplo.com", CNPJ, Perfil.GESTORA).documento
        == "11222333000181"
    )


def test_cadastro_de_gestora_recusa_cpf():
    with pytest.raises(DocumentoInvalidoError):
        validar_cadastro("Ana", "ana@exemplo.com", CPF, Perfil.GESTORA)


def test_documento_invalido():
    with pytest.raises(DocumentoInvalidoError):
        validar_cadastro("Ana", "ana@exemplo.com", "123", Perfil.INVESTIDOR)


def test_email_invalido():
    with pytest.raises(EmailInvalidoError):
        validar_cadastro("Ana", "sem-arroba", CPF, Perfil.INVESTIDOR)


@pytest.mark.parametrize(("nome", "email"), [("", "a@b.com"), ("Ana", ""), ("  ", "a@b.com")])
def test_campos_em_branco(nome, email):
    with pytest.raises(DadosIncompletosError):
        validar_cadastro(nome, email, CPF, Perfil.INVESTIDOR)
