"""
Regras de identidade: normalização e validação de documentos e e-mail.

A normalização de documento é a regra mais crítica da plataforma inteira em
silêncio: o CPF/CNPJ normalizado é a chave que liga o usuário logado aos seus
aportes no BigQuery. Se as normalizações usadas em cadastro, login e consulta
divergirem, o investidor vê um dashboard vazio mesmo tendo aportes. Agora é
uma função só.
"""

import re
from typing import Final

from validate_docbr import CNPJ, CPF

# Validação básica de formato de e-mail — não verifica se o domínio existe.
_EMAIL_REGEX: Final[re.Pattern[str]] = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# CPF tem 11 dígitos, CNPJ tem 14; `validar` confere os dígitos verificadores.
_REGRAS_DOCUMENTOS: Final[dict[str, dict]] = {
    "CPF": {"tamanho": 11, "permite_letras": False, "validar": CPF().validate},
    "CNPJ": {"tamanho": 14, "permite_letras": False, "validar": CNPJ().validate},
}

DOCUMENTO_INVALIDO: Final[str] = "INVALIDO"


def normalizar_documento(documento: str | None) -> str:
    """
    Reduz um CPF/CNPJ a somente dígitos.

    É a chave de ligação entre usuário e aportes. Usada no cadastro, no login e
    nas consultas ao BigQuery — todas precisam concordar.

    Args:
        documento (str | None): Documento em qualquer formato, ou None.

    Returns:
        str: Apenas os dígitos. String vazia quando a entrada é vazia ou None.
    """
    return re.sub(r"[^0-9]", "", str(documento or ""))


def identificar_documento(documento_bruto: str) -> tuple[str, str]:
    """
    Classifica uma string como CPF, CNPJ ou inválida, e devolve a versão limpa.

    COMO FUNCIONA:
        1. Remove tudo que não for letra ou número.
        2. Compara o tamanho com as regras de cada tipo e exige só dígitos.
        3. Confere os dígitos verificadores (`validate-docbr`). Sequências repetidas,
           como '00000000000', são recusadas.
        CNPJ alfanumérico ainda é recusado de propósito: `normalizar_documento`, a
        chave de ligação com os aportes, só mantém dígitos.

    Args:
        documento_bruto (str): String digitada pelo usuário, com ou sem máscara.

    Returns:
        tuple[str, str]: ('CPF' | 'CNPJ' | 'INVALIDO', documento sem formatação).
    """
    # Letras são mantidas aqui para que um documento alfanumérico do tamanho certo
    # seja REJEITADO explicitamente, em vez de virar um CPF ao perder as letras.
    documento_limpo = re.sub(r"[^a-zA-Z0-9]", "", str(documento_bruto)).upper()
    tamanho = len(documento_limpo)

    for tipo, regras in _REGRAS_DOCUMENTOS.items():
        if tamanho != regras["tamanho"]:
            continue
        if not regras["permite_letras"] and not documento_limpo.isdigit():
            continue
        if not regras["validar"](documento_limpo):
            continue
        return tipo, documento_limpo

    return DOCUMENTO_INVALIDO, documento_limpo


def normalizar_email(email: str | None) -> str:
    """
    Normaliza um e-mail para uso como login.

    Args:
        email (str | None): E-mail digitado.

    Returns:
        str: E-mail sem espaços nas pontas e em minúsculas.
    """
    return (email or "").strip().lower()


def email_tem_formato_valido(email: str) -> bool:
    """
    Verifica se o e-mail tem formato plausível.

    Args:
        email (str): E-mail já normalizado.

    Returns:
        bool: True se casa com a regex básica de formato.
    """
    return bool(_EMAIL_REGEX.match(email))
