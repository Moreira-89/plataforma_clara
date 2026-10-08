"""
Perfis de acesso e validação de cadastro.

Regras puras: não conhece Firebase, FastAPI nem banco. O perfil viaja numa claim do
token; o documento (CPF/CNPJ) é a chave que liga o usuário aos seus aportes.

COMO FUNCIONA:
    1. `perfil_de_claims` lê a claim `perfil` de um token já verificado.
    2. `validar_cadastro` normaliza e valida nome, e-mail e documento.
    3. Investidor aceita CPF ou CNPJ; gestora só aceita CNPJ.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    PerfilAusenteError: Claim `perfil` ausente ou desconhecida.
    DadosIncompletosError: Nome ou e-mail em branco.
    EmailInvalidoError: E-mail fora do formato.
    DocumentoInvalidoError: Documento inválido, ou CPF para uma gestora.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.domain import identidade
from app.domain.erros import (
    DadosIncompletosError,
    DocumentoInvalidoError,
    EmailInvalidoError,
    PerfilAusenteError,
)


class Perfil(StrEnum):
    """Perfis de acesso da plataforma."""

    INVESTIDOR = "investidor"
    GESTORA = "gestora"


@dataclass(frozen=True)
class DadosCadastro:
    """Dados de um cadastro já normalizados e validados."""

    nome: str
    email: str
    documento: str
    tipo_documento: str


def perfil_de_claims(claims: Mapping[str, Any]) -> Perfil:
    """
    Lê o perfil das claims de um token já verificado.

    Args:
        claims (Mapping[str, Any]): Claims do token.

    Returns:
        Perfil: O perfil do usuário.

    Raises:
        PerfilAusenteError: Se a claim `perfil` não existe ou não é um perfil conhecido.
    """
    try:
        return Perfil(claims.get("perfil"))
    except ValueError:
        raise PerfilAusenteError("O token não traz um perfil válido.") from None


def validar_cadastro(nome: str, email: str, documento: str, perfil: Perfil) -> DadosCadastro:
    """
    Normaliza e valida os dados de um cadastro.

    Args:
        nome (str): Nome do usuário.
        email (str): E-mail, em qualquer caixa.
        documento (str): CPF ou CNPJ, com ou sem máscara.
        perfil (Perfil): Perfil que está sendo cadastrado.

    Returns:
        DadosCadastro: Dados normalizados.

    Raises:
        DadosIncompletosError: Nome ou e-mail em branco.
        EmailInvalidoError: E-mail fora do formato.
        DocumentoInvalidoError: Documento inválido, ou CPF para uma gestora.
    """
    nome = (nome or "").strip()
    email = identidade.normalizar_email(email)
    if not nome or not email:
        raise DadosIncompletosError("Nome e e-mail são obrigatórios.")
    if not identidade.email_tem_formato_valido(email):
        raise EmailInvalidoError("E-mail com formato inválido.")

    tipo, limpo = identidade.identificar_documento(documento)
    if tipo == identidade.DOCUMENTO_INVALIDO:
        raise DocumentoInvalidoError("CPF/CNPJ inválido.")
    if perfil is Perfil.GESTORA and tipo != "CNPJ":
        raise DocumentoInvalidoError("A gestora precisa de um CNPJ.")

    return DadosCadastro(nome=nome, email=email, documento=limpo, tipo_documento=tipo)
