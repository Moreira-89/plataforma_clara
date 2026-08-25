"""
Testes de caracterização das regras de identidade e senha.

Cobre as duas regras de autenticação que precisam sobreviver intactas à migração:
a classificação de CPF/CNPJ e o hash bcrypt. Ambas atravessam a fronteira Reflex →
FastAPI sem poder mudar: os hashes já gravados no banco precisam continuar validando
depois da migração, senão todos os usuários existentes perdem o acesso.

O fluxo de login em si (`AutenticacaoState.fazer_login`) não é testado aqui — ele
depende da máquina de estados do Reflex e some na Fase 2, quando virar um endpoint
`POST /auth/login` com JWT.
"""

from __future__ import annotations

import pytest

pytest.importorskip("reflex", reason="requer o stack completo do Reflex instalado")

import bcrypt  # noqa: E402

from plataforma_clara.states.cadastro_usuario_state import (  # noqa: E402
    CadastroUsuarioState,
)

_identificar = CadastroUsuarioState._identificar_e_limpar_documento
_hash_senha = CadastroUsuarioState._gerar_hash_senha


# -----------------------------------------------------------------------------
# CLASSIFICAÇÃO DE DOCUMENTOS
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "tipo_esperado", "limpo_esperado"),
    [
        ("123.456.789-01", "CPF", "12345678901"),
        ("12345678901", "CPF", "12345678901"),
        ("12.345.678/0001-99", "CNPJ", "12345678000199"),
        ("12345678000199", "CNPJ", "12345678000199"),
    ],
)
def test_documentos_validos_sao_classificados_pelo_tamanho(entrada, tipo_esperado, limpo_esperado):
    """11 dígitos = CPF, 14 = CNPJ. É o tamanho que decide, não o formato da máscara."""
    tipo, limpo = _identificar(entrada)

    assert tipo == tipo_esperado
    assert limpo == limpo_esperado


@pytest.mark.parametrize(
    "entrada",
    ["123", "", "1234567890123456789", "abcdefghijk"],
)
def test_documentos_com_tamanho_errado_sao_invalidos(entrada):
    """Qualquer coisa fora de 11/14 dígitos é rejeitada no cadastro."""
    tipo, _limpo = _identificar(entrada)

    assert tipo == "INVALIDO"


def test_validacao_e_apenas_estrutural_nao_verifica_digitos():
    """
    CARACTERIZAÇÃO DE LIMITAÇÃO CONHECIDA: "00000000000" tem 11 dígitos e passa como
    CPF, apesar de ser um documento impossível. Os dígitos verificadores não são
    conferidos — decisão consciente do MVP, documentada na docstring do código.

    Se a Fase 2 adicionar validação real de DV, este teste quebra de propósito.
    """
    tipo, _limpo = _identificar("00000000000")

    assert tipo == "CPF"


def test_documento_alfanumerico_do_tamanho_certo_e_rejeitado():
    """
    O CNPJ alfanumérico entra em vigor em 2026, mas as regras atuais exigem só dígitos
    (`permite_letras: False`). Fica registrado para virar decisão explícita na migração.
    """
    tipo, _limpo = _identificar("12ABC678000199")

    assert tipo == "INVALIDO"


# -----------------------------------------------------------------------------
# HASH DE SENHA
# -----------------------------------------------------------------------------


def test_hash_bcrypt_valida_a_senha_original():
    """O contrato mínimo: o hash gerado precisa validar contra a senha que o originou."""
    hash_gerado = _hash_senha("senha-secreta-123")

    assert bcrypt.checkpw(b"senha-secreta-123", hash_gerado.encode("utf-8"))


def test_hash_bcrypt_rejeita_senha_errada():
    assert not bcrypt.checkpw(b"senha-errada", _hash_senha("senha-certa").encode("utf-8"))


def test_hashes_da_mesma_senha_sao_diferentes():
    """
    Salt aleatório por hash: duas contas com a mesma senha produzem hashes distintos.
    Sem isso, um vazamento do banco revelaria quais usuários compartilham senha.
    """
    assert _hash_senha("mesma-senha") != _hash_senha("mesma-senha")


def test_hash_usa_o_cost_factor_12():
    """
    O prefixo do hash carrega o custo (`$2b$12$`). A migração para FastAPI NÃO pode
    baixar esse custo: hashes antigos continuariam válidos, mas as senhas novas
    ficariam mais fáceis de quebrar — uma regressão de segurança silenciosa.
    """
    assert _hash_senha("qualquer").startswith("$2b$12$")


def test_hash_e_armazenado_como_string_utf8():
    """O SQLModel grava str, não bytes — a conversão precisa acontecer no serviço."""
    resultado = _hash_senha("qualquer")

    assert isinstance(resultado, str)
