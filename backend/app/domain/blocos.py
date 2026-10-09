"""
Regras do Bloco de Liquidez: etiquetas, código, alocação do capital e validação.

Regras puras: não conhece BigQuery nem FastAPI. Recebe o relógio e o id de fora, para
o resultado ser reproduzível nos testes.

COMO FUNCIONA:
    1. `ETIQUETAS` mapeia cada pedra à sua cor; o código do bloco usa o nome sem acento.
    2. `montar_bloco` valida capital, vencimento, responsável, observação e empresas.
    3. A soma das porcentagens por empresa precisa fechar exatamente 100%.
    4. O capital estimado de cada empresa é o capital total vezes a porcentagem.
    5. A data de criação é a do dia (fuso de Brasília) e o código leva o instante em ms.

Args:
    Nenhum.

Returns:
    BlocoValidado: via `montar_bloco()`.

Raises:
    BlocoInvalidoError: Qualquer regra violada, com a mensagem para a gestora.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from app.domain.erros import BlocoInvalidoError

# Pedras raras usadas como etiqueta, com a cor de cada uma.
ETIQUETAS: Final[dict[str, str]] = {
    "Diamante": "#E8F4F8",
    "Rubi": "#E0115F",
    "Safira": "#0F52BA",
    "Esmeralda": "#50C878",
    "Alexandrita": "#4B5320",
    "Tanzanita": "#6A5ACD",
    "Turmalina Paraíba": "#00E5EE",
    "Opala Negra": "#0B0B1E",
    "Jadeíte": "#40826D",
    "Taaffeite": "#D8BFD8",
    "Grandidierite": "#2F4F4F",
    "Musgravite": "#4A3B4E",
    "Painita": "#7B1818",
    "Benitoíta": "#3F00FF",
    "Poudretteite": "#FFC0CB",
}

# O Brasil não tem horário de verão desde 2019, então o fuso é fixo.
FUSO_BRASIL: Final[timezone] = timezone(timedelta(hours=-3))

LIMITE_OBSERVACAO: Final[int] = 500
LIMITE_RESPONSAVEL: Final[int] = 120

_CENTAVOS: Final[Decimal] = Decimal("0.01")
_CEM: Final[Decimal] = Decimal(100)


@dataclass(frozen=True)
class EmpresaCatalogo:
    """Uma empresa do cadastro, como a busca a devolve."""

    id_empresa: str
    nome_fantasia: str
    razao_social: str
    cnpj: str
    ramo_atividade: str


@dataclass(frozen=True)
class AlocacaoEmpresa:
    """Entrada: a empresa escolhida e a porcentagem do capital que ela recebe."""

    id_empresa: str
    percentual: Decimal


@dataclass(frozen=True)
class EmpresaAlocada:
    """Saída: a alocação já com o capital estimado calculado."""

    id_empresa: str
    percentual: Decimal
    capital_estimado: Decimal


@dataclass(frozen=True)
class BlocoValidado:
    """Bloco pronto para gravar."""

    id_bloco: str
    codigo_identificacao: str
    etiqueta: str
    capital_total: Decimal
    data_criacao: date
    data_vencimento: date
    responsavel_tecnico: str
    observacao: str
    criado_em: datetime
    empresas: tuple[EmpresaAlocada, ...]


def slug_etiqueta(etiqueta: str) -> str:
    """Nome da etiqueta sem acento, em maiúsculas e com `_`, para o código do bloco."""
    sem_acento = unicodedata.normalize("NFKD", etiqueta).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "_", sem_acento.upper()).strip("_")


def _tem_duas_casas(valor: Decimal) -> bool:
    return valor == valor.quantize(_CENTAVOS)


def montar_bloco(
    etiqueta: str,
    capital_total: Decimal,
    data_vencimento: date,
    responsavel_tecnico: str,
    observacao: str | None,
    alocacoes: Sequence[AlocacaoEmpresa],
    *,
    agora: datetime,
    id_bloco: str,
) -> BlocoValidado:
    """
    Valida os dados do formulário e calcula o capital de cada empresa.

    Args:
        etiqueta (str): Nome da pedra, como em `ETIQUETAS`.
        capital_total (Decimal): Capital do bloco em R$, com até duas casas.
        data_vencimento (date): Vencimento do bloco, depois do dia da criação.
        responsavel_tecnico (str): Nome do responsável técnico.
        observacao (str | None): Nota livre da gestora, de até 500 caracteres.
        alocacoes (Sequence[AlocacaoEmpresa]): Empresas e porcentagens.
        agora (datetime): Instante da criação, com fuso.
        id_bloco (str): Identificador gerado por quem chama.

    Returns:
        BlocoValidado: Dados normalizados, com código e datas preenchidos.

    Raises:
        BlocoInvalidoError: Etiqueta, capital, vencimento, responsável, observação ou
            alocação inválidos, ou soma das porcentagens diferente de 100%.
    """
    if etiqueta not in ETIQUETAS:
        raise BlocoInvalidoError("Etiqueta inválida.")

    if capital_total <= 0 or not _tem_duas_casas(capital_total):
        raise BlocoInvalidoError(
            "O capital total deve ser maior que zero, com até 2 casas decimais."
        )

    data_criacao = agora.astimezone(FUSO_BRASIL).date()
    if data_vencimento <= data_criacao:
        raise BlocoInvalidoError("O vencimento deve ser depois da data de criação.")

    responsavel = (responsavel_tecnico or "").strip()
    if not responsavel or len(responsavel) > LIMITE_RESPONSAVEL:
        raise BlocoInvalidoError(
            f"Informe o responsável técnico (até {LIMITE_RESPONSAVEL} caracteres)."
        )

    nota = (observacao or "").strip()
    if len(nota) > LIMITE_OBSERVACAO:
        raise BlocoInvalidoError(f"A observação passa de {LIMITE_OBSERVACAO} caracteres.")

    if not alocacoes:
        raise BlocoInvalidoError("Adicione pelo menos uma empresa ao bloco.")
    ids = [a.id_empresa for a in alocacoes]
    if len(set(ids)) != len(ids):
        raise BlocoInvalidoError("Há empresas repetidas no bloco.")
    for a in alocacoes:
        if not 0 < a.percentual <= _CEM or not _tem_duas_casas(a.percentual):
            raise BlocoInvalidoError(
                "Cada porcentagem deve ficar entre 0 e 100, com até 2 casas decimais."
            )

    soma = sum((a.percentual for a in alocacoes), Decimal(0))
    if soma != _CEM:
        raise BlocoInvalidoError(f"As porcentagens somam {soma}%; elas precisam fechar 100%.")

    empresas = tuple(
        EmpresaAlocada(
            id_empresa=a.id_empresa,
            percentual=a.percentual,
            capital_estimado=(capital_total * a.percentual / _CEM).quantize(
                _CENTAVOS, ROUND_HALF_UP
            ),
        )
        for a in alocacoes
    )
    return BlocoValidado(
        id_bloco=id_bloco,
        codigo_identificacao=f"BLOCO_{slug_etiqueta(etiqueta)}_{int(agora.timestamp() * 1000)}",
        etiqueta=etiqueta,
        capital_total=capital_total,
        data_criacao=data_criacao,
        data_vencimento=data_vencimento,
        responsavel_tecnico=responsavel,
        observacao=nota,
        criado_em=agora,
        empresas=empresas,
    )
