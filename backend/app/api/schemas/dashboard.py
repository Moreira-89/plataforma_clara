"""
Contratos de resposta dos dashboards.

COMO FUNCIONA:
    1. Cada dashboard junta os KPIs consolidados e a tabela da sua visão.
    2. As peças vêm de `contratos.py` e são montadas por `domain/metricas.py`.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from pydantic import BaseModel

from app.api.schemas.contratos import KpisConsolidados, LinhaTabelaGestora, LinhaTransparencia


class DashboardGestora(BaseModel):
    """KPIs e tabela de empresas do dashboard da gestora."""

    kpis: KpisConsolidados
    empresas: list[LinhaTabelaGestora]


class DashboardInvestidor(BaseModel):
    """KPIs e tabela de transparência do dashboard do investidor."""

    kpis: KpisConsolidados
    transparencia: list[LinhaTransparencia]
