"""
Testes das regras de identidade, senha e do fluxo de autenticação.

Cobre `domain/identidade.py`, `domain/seguranca.py` e `services/autenticacao_service.py`.
São as regras que precisam atravessar a fronteira Reflex → FastAPI sem mudar: os
hashes já gravados no banco têm que continuar validando depois da migração, senão
todos os usuários existentes perdem o acesso.

Antes da Fase 1 estas funções eram métodos estáticos de `CadastroUsuarioState` e só
podiam ser testadas carregando o Reflex inteiro. Agora não dependem de framework
nenhum — o que é exatamente o objetivo da extração do domínio.
"""

from __future__ import annotations

import pytest

pytest.importorskip("bcrypt", reason="requer bcrypt instalado")

import bcrypt  # noqa: E402

from plataforma_clara.domain import identidade, seguranca  # noqa: E402
from plataforma_clara.domain.erros import (  # noqa: E402
    DadosIncompletosError,
    DocumentoInvalidoError,
    EmailJaCadastradoError,
)

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
    tipo, limpo = identidade.identificar_documento(entrada)

    assert tipo == tipo_esperado
    assert limpo == limpo_esperado


@pytest.mark.parametrize(
    "entrada",
    ["123", "", "1234567890123456789", "abcdefghijk"],
)
def test_documentos_com_tamanho_errado_sao_invalidos(entrada):
    """Qualquer coisa fora de 11/14 dígitos é rejeitada no cadastro."""
    tipo, _limpo = identidade.identificar_documento(entrada)

    assert tipo == identidade.DOCUMENTO_INVALIDO


def test_validacao_e_apenas_estrutural_nao_verifica_digitos():
    """
    CARACTERIZAÇÃO DE LIMITAÇÃO CONHECIDA: "00000000000" tem 11 dígitos e passa como
    CPF, apesar de ser um documento impossível. Os dígitos verificadores não são
    conferidos — decisão consciente do MVP, documentada na docstring do código.

    Se a Fase 2 adicionar validação real de DV, este teste quebra de propósito.
    """
    tipo, _limpo = identidade.identificar_documento("00000000000")

    assert tipo == "CPF"


def test_documento_alfanumerico_do_tamanho_certo_e_rejeitado():
    """
    O CNPJ alfanumérico entra em vigor em 2026, mas as regras atuais exigem só dígitos
    (`permite_letras: False`). Fica registrado para virar decisão explícita na migração.
    """
    tipo, _limpo = identidade.identificar_documento("12ABC678000199")

    assert tipo == identidade.DOCUMENTO_INVALIDO


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("123.456.789-01", "12345678901"),
        ("12.345.678/0001-99", "12345678000199"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalizacao_de_documento_e_a_mesma_em_toda_a_plataforma(entrada, esperado):
    """
    REGRESSÃO DA FASE 1: cadastro, login, CSV e relatório normalizavam o documento
    cada um por conta própria. Agora todos chamam esta função. Se as normalizações
    divergirem, o investidor vê um dashboard vazio apesar de ter aportes.
    """
    assert identidade.normalizar_documento(entrada) == esperado


# -----------------------------------------------------------------------------
# E-MAIL
# -----------------------------------------------------------------------------


def test_email_e_normalizado_para_minusculas_sem_espacos():
    """O e-mail é a chave de login: gravar e buscar precisam usar a mesma forma."""
    assert identidade.normalizar_email("  Fulano@Exemplo.COM  ") == "fulano@exemplo.com"


@pytest.mark.parametrize("email", ["a@b.co", "nome.sobrenome+tag@dominio.com.br"])
def test_emails_plausiveis_sao_aceitos(email):
    assert identidade.email_tem_formato_valido(email)


@pytest.mark.parametrize("email", ["sem-arroba", "@dominio.com", "nome@sem-tld", ""])
def test_emails_malformados_sao_rejeitados(email):
    assert not identidade.email_tem_formato_valido(email)


# -----------------------------------------------------------------------------
# HASH DE SENHA
# -----------------------------------------------------------------------------


def test_hash_bcrypt_valida_a_senha_original():
    """O contrato mínimo: o hash gerado precisa validar contra a senha que o originou."""
    hash_gerado = seguranca.gerar_hash_senha("senha-secreta-123")

    assert bcrypt.checkpw(b"senha-secreta-123", hash_gerado.encode("utf-8"))


def test_hash_bcrypt_rejeita_senha_errada():
    assert not seguranca.senha_confere("senha-errada", seguranca.gerar_hash_senha("senha-certa"))


def test_hashes_da_mesma_senha_sao_diferentes():
    """
    Salt aleatório por hash: duas contas com a mesma senha produzem hashes distintos.
    Sem isso, um vazamento do banco revelaria quais usuários compartilham senha.
    """
    assert seguranca.gerar_hash_senha("mesma-senha") != seguranca.gerar_hash_senha("mesma-senha")


def test_hash_usa_o_cost_factor_12():
    """
    O prefixo do hash carrega o custo (`$2b$12$`). A migração para FastAPI NÃO pode
    baixar esse custo: hashes antigos continuariam válidos, mas as senhas novas
    ficariam mais fáceis de quebrar — uma regressão de segurança silenciosa.
    """
    assert seguranca.gerar_hash_senha("qualquer").startswith("$2b$12$")


def test_hash_e_armazenado_como_string_utf8():
    """O SQLModel grava str, não bytes — a conversão acontece no domínio."""
    assert isinstance(seguranca.gerar_hash_senha("qualquer"), str)


@pytest.mark.parametrize("hash_ruim", ["", "não é um hash", None])
def test_hash_corrompido_no_banco_nao_derruba_o_login(hash_ruim):
    """
    Um hash inválido gravado por qualquer motivo devolve False, não uma exceção:
    para quem tenta entrar, o resultado é o mesmo de senha errada.
    """
    assert seguranca.senha_confere("qualquer", hash_ruim) is False


# -----------------------------------------------------------------------------
# FLUXO DE AUTENTICAÇÃO
# -----------------------------------------------------------------------------

pytest.importorskip("sqlmodel", reason="requer o stack de banco instalado")

from plataforma_clara.domain.models import Usuario  # noqa: E402
from plataforma_clara.domain.schemas import UsuarioCriacao  # noqa: E402
from plataforma_clara.services import autenticacao_service  # noqa: E402


def _usuario(senha: str = "senha-certa") -> Usuario:
    return Usuario(
        tipo_usuario="investidor",
        nome_usuario="Fulano de Tal",
        email_usuario="fulano@exemplo.com",
        identificador_usuario="123.456.789-01",
        senha_hash_usuario=seguranca.gerar_hash_senha(senha),
    )


def test_login_valido_devolve_documento_normalizado(fabricar_sessao_fake):
    """
    O documento devolvido no login É a chave de filtro dos aportes. Ele precisa sair
    daqui somente com dígitos, mesmo que o cadastro tenha gravado com máscara.
    """
    fabrica = fabricar_sessao_fake(objetos=[_usuario()])

    autenticado = autenticacao_service.autenticar(
        "Fulano@Exemplo.com", "senha-certa", sessao_factory=fabrica
    )

    assert autenticado is not None
    assert autenticado.documento == "12345678901"
    assert autenticado.tipo_usuario == "investidor"


def test_login_com_senha_errada_devolve_none(fabricar_sessao_fake):
    fabrica = fabricar_sessao_fake(objetos=[_usuario()])

    assert (
        autenticacao_service.autenticar(
            "fulano@exemplo.com", "senha-errada", sessao_factory=fabrica
        )
        is None
    )


def test_login_de_email_inexistente_devolve_none(fabricar_sessao_fake):
    """Mesmo retorno de senha errada: a resposta não revela se o e-mail existe."""
    fabrica = fabricar_sessao_fake(objetos=[])

    assert (
        autenticacao_service.autenticar("ninguem@exemplo.com", "qualquer", sessao_factory=fabrica)
        is None
    )


def test_login_sem_credenciais_nem_consulta_o_banco(fabricar_sessao_fake):
    """Campo vazio é barrado antes da consulta — não gasta conexão nem tempo de bcrypt."""
    fabrica = fabricar_sessao_fake(objetos=[_usuario()])

    assert autenticacao_service.autenticar("", "", sessao_factory=fabrica) is None
    assert fabrica().consultas_orm == 0


def test_cadastro_grava_documento_normalizado_e_senha_em_hash(fabricar_sessao_fake):
    """
    Duas garantias num teste só: o documento entra no banco sem máscara (para casar
    com o filtro dos aportes) e a senha NUNCA entra em texto plano.
    """
    fabrica = fabricar_sessao_fake(objetos=[])
    dados = UsuarioCriacao(
        tipo_usuario="investidor",
        nome_usuario="  Fulano  ",
        email_usuario="Fulano@Exemplo.com",
        identificador_usuario="123.456.789-01",
        senha="minha-senha",
    )

    autenticacao_service.registrar_usuario(dados, sessao_factory=fabrica)

    gravado = fabrica().adicionados[0]
    assert gravado.identificador_usuario == "12345678901"
    assert gravado.email_usuario == "fulano@exemplo.com"
    assert gravado.nome_usuario == "Fulano"
    assert gravado.senha_hash_usuario != "minha-senha"
    assert seguranca.senha_confere("minha-senha", gravado.senha_hash_usuario)


def test_cadastro_com_email_duplicado_e_recusado(fabricar_sessao_fake):
    """A verificação prévia existe para dar mensagem clara em vez de erro de constraint."""
    fabrica = fabricar_sessao_fake(objetos=[_usuario()])
    dados = UsuarioCriacao(
        tipo_usuario="investidor",
        nome_usuario="Outro",
        email_usuario="fulano@exemplo.com",
        identificador_usuario="12345678901",
        senha="123",
    )

    with pytest.raises(EmailJaCadastradoError):
        autenticacao_service.registrar_usuario(dados, sessao_factory=fabrica)

    assert fabrica().adicionados == []


@pytest.mark.parametrize(
    ("campo", "valor", "erro"),
    [
        ("tipo_usuario", "hacker", DadosIncompletosError),
        ("nome_usuario", "", DadosIncompletosError),
        ("email_usuario", "sem-arroba", DadosIncompletosError),
        ("identificador_usuario", "123", DocumentoInvalidoError),
    ],
)
def test_cadastro_invalido_nao_chega_ao_banco(fabricar_sessao_fake, campo, valor, erro):
    """Toda validação acontece antes de abrir a sessão — inclusive a do perfil de acesso."""
    fabrica = fabricar_sessao_fake(objetos=[])
    campos = {
        "tipo_usuario": "investidor",
        "nome_usuario": "Fulano",
        "email_usuario": "fulano@exemplo.com",
        "identificador_usuario": "12345678901",
        "senha": "123",
    }
    campos[campo] = valor

    with pytest.raises(erro):
        autenticacao_service.registrar_usuario(UsuarioCriacao(**campos), sessao_factory=fabrica)

    assert fabrica().adicionados == []
