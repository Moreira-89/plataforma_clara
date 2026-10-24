"""
Dados e regras do painel da gestora (visão geral).

COMO FUNCIONA:
    1. Os dataclasses descrevem o que o painel mostra: resumo e série do mercado de FIDCs,
       carteira por nota SCR, benchmark por setor, blocos com score, distribuição dos scores
       das empresas e empresas dos blocos com alerta.
    2. Todas as taxas e participações circulam em porcentagem (8,32 = 8,32%).
    3. As funções puras convertem fração em porcentagem, calculam variações, a média do score,
       o capital por nota e a exposição dos blocos por setor.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from dataclasses import dataclass, field
from datetime import date

from app.domain import risco

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
class PontoMercado:
    """Indicadores do mercado de FIDCs em um mês."""

    mes: date
    inadimplencia: float
    pl_total: float
    fundos_ativos: int


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
    grupo: str
    participacao_mercado: float
    participacao_no_grupo: float | None
    inadimplencia: float | None


@dataclass(frozen=True, slots=True)
class ComponentesScore:
    """Pontos de cada componente do score, ponderados pelo capital das empresas do bloco."""

    qualidade_fundos: float
    permanencia: float
    risco_setor: float
    aceitacao: float


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
    componentes: ComponentesScore | None = None


@dataclass(frozen=True, slots=True)
class CapitalPorNota:
    """Capital dos blocos que têm uma mesma nota."""

    nota: str
    quantidade: int
    capital: float


@dataclass(frozen=True, slots=True)
class ExposicaoSetor:
    """Peso do setor no capital dos blocos, ao lado do peso dele na economia real do mercado."""

    setor: str
    capital: float
    participacao_blocos: float
    participacao_mercado: float | None
    inadimplencia: float | None


@dataclass(frozen=True, slots=True)
class FaixaDeScore:
    """Empresas com score entre `inicio` e `inicio + 9,99`."""

    inicio: int
    empresas: int
    perfil_compartilhado: int


@dataclass(frozen=True, slots=True)
class EmpresaComAlerta:
    """Empresa de um bloco cujo score traz um alerta de qualidade."""

    id_empresa: str
    nome: str
    etiqueta: str
    score: float
    alerta: str


@dataclass(frozen=True, slots=True)
class PainelDaGestora:
    """Tudo o que a visão geral da gestora desenha."""

    mercado: ResumoMercado | None
    serie_mercado: list[PontoMercado]
    rating: list[FaixaRating]
    setores: list[SetorBenchmark]
    blocos: list[BlocoDoPainel]
    exposicao: list[ExposicaoSetor]
    distribuicao_scores: list[FaixaDeScore]
    alertas: list[EmpresaComAlerta]


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


def capital_por_nota(blocos: list[BlocoDoPainel]) -> list[CapitalPorNota]:
    """Soma o capital dos blocos por nota, da melhor para a pior; ignora blocos sem nota."""
    somas: dict[str, list[float]] = {}
    for bloco in blocos:
        if bloco.nota is None:
            continue
        quantidade, capital = somas.setdefault(bloco.nota, [0, 0.0])
        somas[bloco.nota] = [quantidade + 1, capital + bloco.capital_total]
    ordem = sorted(somas, key=lambda n: (risco.ordem_da_nota(n), n))
    return [CapitalPorNota(n, int(somas[n][0]), somas[n][1]) for n in ordem]


def montar_exposicao(
    capital_por_setor: dict[str, float], setores: list[SetorBenchmark]
) -> list[ExposicaoSetor]:
    """
    Compara o capital dos blocos por setor com o peso do setor na economia real do mercado.

    Só os setores do grupo "Economia real" têm peso comparável; os demais ficam sem referência.
    """
    total = sum(capital_por_setor.values())
    if not total:
        return []
    por_nome = {s.setor: s for s in setores}
    exposicao = []
    for nome, capital in capital_por_setor.items():
        ref = por_nome.get(nome)
        comparavel = ref is not None and ref.grupo == "Economia real"
        exposicao.append(
            ExposicaoSetor(
                setor=nome,
                capital=capital,
                participacao_blocos=capital / total * 100,
                participacao_mercado=ref.participacao_no_grupo if comparavel else None,
                inadimplencia=ref.inadimplencia if ref else None,
            )
        )
    return sorted(exposicao, key=lambda e: -e.participacao_blocos)
