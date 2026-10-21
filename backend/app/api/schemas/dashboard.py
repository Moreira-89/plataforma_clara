"""
Contratos de resposta dos dashboards.

COMO FUNCIONA:
    1. O dashboard da gestora é a visão geral: mercado de FIDCs (CVM), rating, setores e blocos.
    2. O do investidor junta os KPIs consolidados e a tabela de transparência (`contratos.py`).
    3. Taxas e participações vão em porcentagem (8,32 = 8,32%).

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from datetime import date

from pydantic import BaseModel

from app.api.schemas.contratos import KpisConsolidados, LinhaTransparencia


class ResumoMercado(BaseModel):
    """Foto do mercado de FIDCs no último mês informado à CVM."""

    referencia: date
    fundos_ativos: int
    pl_total: float
    var_pl_mes: float | None
    inadimplencia: float
    var_inadimplencia_pp: float | None
    inadimplencia_acima_90: float


class PontoInadimplencia(BaseModel):
    """Inadimplência do mercado em um mês."""

    mes: date
    inadimplencia: float


class FaixaRating(BaseModel):
    """Parcela da carteira do mercado em uma nota SCR."""

    nota: str
    participacao: float
    valor: float


class SetorBenchmark(BaseModel):
    """Peso do setor no mercado e inadimplência dos fundos concentrados nele."""

    setor: str
    participacao_mercado: float
    inadimplencia: float | None


class BlocoDoPainel(BaseModel):
    """Bloco de liquidez com score e a cor da sua etiqueta."""

    id_bloco: str
    codigo: str
    etiqueta: str
    cor: str | None
    capital_total: float
    qtd_empresas: int
    score: float | None
    nota: str | None
    setores: list[str]


class ResumoBlocos(BaseModel):
    """Totais dos blocos da gestora."""

    quantidade: int
    capital_total: float
    score_medio: float | None


class DashboardGestora(BaseModel):
    """Visão geral da gestora: mercado, rating, setores e blocos."""

    mercado: ResumoMercado | None
    inadimplencia: list[PontoInadimplencia]
    rating: list[FaixaRating]
    setores: list[SetorBenchmark]
    resumo_blocos: ResumoBlocos
    blocos: list[BlocoDoPainel]


class DashboardInvestidor(BaseModel):
    """KPIs e tabela de transparência do dashboard do investidor."""

    kpis: KpisConsolidados
    transparencia: list[LinhaTransparencia]
