"""
Contratos de resposta dos dashboards.

COMO FUNCIONA:
    1. O dashboard da gestora é a visão geral: mercado de FIDCs (CVM), rating, setores e blocos.
    2. O do investidor junta os KPIs consolidados e a tabela de transparência (`contratos.py`).
    3. Taxas e participações vão em porcentagem (8,32 = 8,32%).
    4. Também trazem a série do mercado, a composição do score, a exposição por setor,
       a distribuição dos scores e as empresas dos blocos com alerta.

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


class PontoMercado(BaseModel):
    """Indicadores do mercado de FIDCs em um mês."""

    mes: date
    inadimplencia: float
    pl_total: float
    fundos_ativos: int


class FaixaRating(BaseModel):
    """Parcela da carteira do mercado em uma nota SCR."""

    nota: str
    participacao: float
    valor: float


class SetorBenchmark(BaseModel):
    """Peso do setor no mercado e inadimplência dos fundos concentrados nele."""

    setor: str
    grupo: str
    participacao_mercado: float
    participacao_no_grupo: float | None
    inadimplencia: float | None


class ComponentesScore(BaseModel):
    """Pontos de cada componente do score do bloco."""

    qualidade_fundos: float
    permanencia: float
    risco_setor: float
    aceitacao: float


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
    componentes: ComponentesScore | None


class CapitalPorNota(BaseModel):
    """Capital dos blocos que têm uma mesma nota."""

    nota: str
    quantidade: int
    capital: float


class ExposicaoSetor(BaseModel):
    """Peso do setor no capital dos blocos e na economia real do mercado."""

    setor: str
    capital: float
    participacao_blocos: float
    participacao_mercado: float | None
    inadimplencia: float | None


class FaixaDeScore(BaseModel):
    """Empresas com score entre `inicio` e `inicio + 9,99`."""

    inicio: int
    empresas: int
    perfil_compartilhado: int


class EmpresaComAlerta(BaseModel):
    """Empresa de um bloco cujo score traz um alerta de qualidade."""

    id_empresa: str
    nome: str
    etiqueta: str
    score: float
    alerta: str


class ResumoBlocos(BaseModel):
    """Totais dos blocos da gestora."""

    quantidade: int
    capital_total: float
    score_medio: float | None


class DashboardGestora(BaseModel):
    """Visão geral da gestora: mercado, rating, setores e blocos."""

    mercado: ResumoMercado | None
    serie_mercado: list[PontoMercado]
    rating: list[FaixaRating]
    setores: list[SetorBenchmark]
    resumo_blocos: ResumoBlocos
    blocos: list[BlocoDoPainel]
    capital_por_nota: list[CapitalPorNota]
    exposicao: list[ExposicaoSetor]
    distribuicao_scores: list[FaixaDeScore]
    alertas: list[EmpresaComAlerta]


class DashboardInvestidor(BaseModel):
    """KPIs e tabela de transparência do dashboard do investidor."""

    kpis: KpisConsolidados
    transparencia: list[LinhaTransparencia]
