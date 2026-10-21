"""
Dados e regras do painel da gestora (visão geral).

COMO FUNCIONA:
    1. Os dataclasses descrevem o que o painel mostra: resumo e série do mercado de FIDCs,
       carteira por nota SCR, benchmark por setor e os blocos com score.
    2. Todas as taxas e participações circulam em porcentagem (8,32 = 8,32%).
    3. As funções puras convertem fração em porcentagem e calculam variações e a média do score.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from dataclasses import dataclass, field
from datetime import date

# Ordem da escala SCR, da melhor nota para a pior.
NOTAS_SCR = ("AA", "A", "B", "C", "D", "E", "F", "G", "H")


@dataclass(frozen=True, slots=True)
class ResumoMercado:
    """Foto do mercado de FIDCs no último mês informado à CVM."""

    referencia: date
    fundos_ativos: int
    pl_total: float
    var_pl_mes: float | None
    inadimplencia: float
    var_inadimplencia_pp: float | None
    inadimplencia_acima_90: float


@dataclass(frozen=True, slots=True)
class PontoInadimplencia:
    """Inadimplência do mercado em um mês."""

    mes: date
    inadimplencia: float


@dataclass(frozen=True, slots=True)
class FaixaRating:
    """Parcela da carteira do mercado em uma nota SCR."""

    nota: str
    participacao: float
    valor: float


@dataclass(frozen=True, slots=True)
class SetorBenchmark:
    """Peso do setor no mercado e inadimplência dos fundos concentrados nele."""

    setor: str
    participacao_mercado: float
    inadimplencia: float | None


@dataclass(frozen=True, slots=True)
class BlocoDoPainel:
    """Bloco de liquidez com o score calculado sobre as suas empresas."""

    id_bloco: str
    codigo: str
    etiqueta: str
    capital_total: float
    qtd_empresas: int
    score: float | None
    nota: str | None
    setores: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PainelDaGestora:
    """Tudo o que a visão geral da gestora desenha."""

    mercado: ResumoMercado | None
    inadimplencia: list[PontoInadimplencia]
    rating: list[FaixaRating]
    setores: list[SetorBenchmark]
    blocos: list[BlocoDoPainel]


def para_percentual(fracao: float | None) -> float | None:
    """Converte uma fração (0,083) em porcentagem (8,3), mantendo o None."""
    return None if fracao is None else float(fracao) * 100


def variacao_percentual(atual: float, anterior: float | None) -> float | None:
    """Variação relativa em % entre dois valores; None sem base de comparação."""
    if anterior is None or anterior == 0:
        return None
    return (atual / anterior - 1) * 100


def diferenca_em_pontos(atual: float, anterior: float | None) -> float | None:
    """Diferença, em pontos percentuais, entre duas taxas já em %."""
    return None if anterior is None else atual - anterior


def score_medio_ponderado(blocos: list[BlocoDoPainel]) -> float | None:
    """Média do score dos blocos pesada pelo capital; ignora blocos sem score."""
    pesos = [(b.score, b.capital_total) for b in blocos if b.score is not None]
    total = sum(peso for _, peso in pesos)
    if not total:
        return None
    return sum(score * peso for score, peso in pesos) / total


def ordenar_rating(faixas: list[FaixaRating]) -> list[FaixaRating]:
    """Coloca as notas na ordem da escala SCR (AA a H)."""
    return sorted(faixas, key=lambda f: NOTAS_SCR.index(f.nota) if f.nota in NOTAS_SCR else 99)
