"""
Investimentos de demonstração: quais blocos cada investidor "já tem" e com quanto.

Não existe mecanismo real de aporte (a fonte dos dados de aportes ainda não foi decidida). Para as
telas do investidor terem o que mostrar, cada conta recebe, de forma sorteada mas ESTÁVEL, alguns
blocos já investidos. Os valores são fictícios, como o resto dos dados de demonstração.

COMO FUNCIONA:
    1. Para cada par (investidor, bloco), um hash SHA-256 gera números pseudoaleatórios.
    2. Cerca de 40% dos blocos entram na carteira do investidor.
    3. O valor investido é um múltiplo de R$ 5 mil, de R$ 5 mil a R$ 500 mil.
    4. Como o resultado depende só do par, o mesmo investidor vê sempre os mesmos blocos e valores,
       outro investidor vê uma carteira diferente, e blocos novos não embaralham os antigos.
    5. `resumir_por_etiqueta` soma a carteira por pedra (uma linha por etiqueta, da maior para a
       menor), para a visão geral do investidor.
    6. `ranquear_empresas` distribui o valor investido em cada bloco entre as empresas dele, pela
       fatia de cada uma, e ordena as empresas da carteira da que mais recebe para a que menos recebe.

Args:
    Nenhum.

Returns:
    Decimal | None: via `valor_investido()`.
    ResumoDaEtiqueta: via `resumir_por_etiqueta()`.
    EmpresaDaCarteira: via `ranquear_empresas()`.

Raises:
    Nenhum.
"""

import hashlib
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from app.domain.blocos import BlocoDetalhado

# Fração dos blocos em que cada investidor "já investiu".
PROPORCAO_INVESTIDA: Final[float] = 0.4

PASSO_DO_VALOR: Final[int] = 5_000
_PASSOS_DO_VALOR: Final[int] = 100  # de R$ 5 mil a R$ 500 mil


def _fracao(sal: str, uid: str, id_bloco: str) -> float:
    """Número em [0, 1) determinado por (sal, investidor, bloco)."""
    resumo = hashlib.sha256(f"{sal}:{uid}:{id_bloco}".encode()).digest()
    return int.from_bytes(resumo[:8], "big") / 2**64


def valor_investido(uid: str, id_bloco: str) -> Decimal | None:
    """
    Quanto o investidor "já investiu" no bloco, ou None se não investiu.

    Args:
        uid (str): Uid do investidor no Firebase.
        id_bloco (str): Identificador do bloco.

    Returns:
        Decimal | None: Valor em R$, múltiplo de 5 mil entre 5 mil e 500 mil; None se o bloco
            não está na carteira dele.
    """
    if _fracao("escolha", uid, id_bloco) >= PROPORCAO_INVESTIDA:
        return None
    passos = 1 + int(_fracao("valor", uid, id_bloco) * _PASSOS_DO_VALOR)
    return Decimal(passos * PASSO_DO_VALOR)


@dataclass(frozen=True)
class ResumoDaEtiqueta:
    """Quanto o investidor tem aplicado numa pedra."""

    etiqueta: str
    total_investido: Decimal
    quantidade_blocos: int
    participacao: float  # fração do total investido, de 0 a 1


def resumir_por_etiqueta(investimentos: Iterable[tuple[str, Decimal]]) -> list[ResumoDaEtiqueta]:
    """
    Soma os investimentos por etiqueta, da maior para a menor; empate segue a ordem alfabética.

    Args:
        investimentos (Iterable[tuple[str, Decimal]]): Pares (etiqueta do bloco, valor investido).

    Returns:
        list[ResumoDaEtiqueta]: Uma linha por etiqueta; vazia se não há investimentos.
    """
    totais: dict[str, Decimal] = defaultdict(Decimal)
    quantidades: dict[str, int] = defaultdict(int)
    for etiqueta, valor in investimentos:
        totais[etiqueta] += valor
        quantidades[etiqueta] += 1
    geral = sum(totais.values(), Decimal(0))
    ordem = sorted(totais, key=lambda e: (-totais[e], e))
    return [ResumoDaEtiqueta(e, totais[e], quantidades[e], float(totais[e] / geral)) for e in ordem]


@dataclass(frozen=True)
class EmpresaDaCarteira:
    """Uma empresa da carteira do investidor e quanto do dinheiro dele está nela."""

    id_empresa: str
    cnpj: str
    nome_fantasia: str | None
    ramo_atividade: str | None
    etiqueta: str
    capital_investido: Decimal
    participacao: float  # fração do total investido, de 0 a 1


def ranquear_empresas(
    carteira: Iterable[tuple[Decimal, BlocoDetalhado]],
) -> list[EmpresaDaCarteira]:
    """
    Ordena as empresas da carteira pelo capital do investidor que cada uma recebe.

    O capital do investidor numa empresa é o valor investido no bloco vezes a fatia da empresa
    nele. Se a mesma empresa aparece em mais de um bloco, os valores se somam.

    Args:
        carteira (Iterable[tuple[Decimal, BlocoDetalhado]]): Pares (valor investido, bloco com
            as empresas).

    Returns:
        list[EmpresaDaCarteira]: Da que mais recebe para a que menos; empate segue o nome.
    """
    capitais: dict[str, Decimal] = defaultdict(Decimal)
    dados = {}
    for valor, detalhado in carteira:
        for empresa in detalhado.empresas:
            fatia = valor * empresa.percentual_liquidez / 100
            capitais[empresa.id_empresa] += fatia.quantize(Decimal("0.01"), ROUND_HALF_UP)
            dados.setdefault(empresa.id_empresa, (empresa, detalhado.bloco.etiqueta))
    geral = sum(capitais.values(), Decimal(0))
    ordem = sorted(capitais, key=lambda i: (-capitais[i], dados[i][0].nome_fantasia or "", i))
    return [
        EmpresaDaCarteira(
            id_empresa=i,
            cnpj=dados[i][0].cnpj,
            nome_fantasia=dados[i][0].nome_fantasia,
            ramo_atividade=dados[i][0].ramo_atividade,
            etiqueta=dados[i][1],
            capital_investido=capitais[i],
            participacao=float(capitais[i] / geral),
        )
        for i in ordem
    ]
