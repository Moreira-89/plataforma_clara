"""
Contratos do resumo da carteira do investidor.

COMO FUNCIONA:
    1. `ResumoEtiqueta` é uma pedra em que o investidor aplicou: total, blocos e participação.
    2. `ResumoInvestimentos` traz o total geral e as pedras, da maior para a menor.
    3. `EmpresaDaCarteira` é uma empresa do ranking, com o capital do investidor nela.
    4. `RendimentoInvestimentos` traz o rendimento mensal dos últimos 12 meses.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ResumoEtiqueta(BaseModel):
    """Uma etiqueta da carteira, com a cor da pedra."""

    etiqueta: str
    cor: str | None
    total_investido: Decimal
    quantidade_blocos: int
    participacao: float


class ResumoInvestimentos(BaseModel):
    """Visão geral da carteira: o total e o que cada etiqueta representa."""

    total_investido: Decimal
    etiquetas: list[ResumoEtiqueta]


class EmpresaDaCarteira(BaseModel):
    """Uma empresa da carteira do investidor, com score e a etiqueta do bloco dela."""

    id_empresa: str
    cnpj: str
    nome_fantasia: str | None
    ramo_atividade: str | None
    etiqueta: str
    cor: str | None
    capital_investido: Decimal
    participacao: float
    score: float | None
    nota_risco: str | None


class RendimentoMes(BaseModel):
    """O rendimento da carteira num mês fechado."""

    mes: date = Field(description="Primeiro dia do mês")
    taxa_percentual: Decimal
    rendimento: Decimal
    acumulado_percentual: Decimal


class RendimentoInvestimentos(BaseModel):
    """Rendimento dos últimos 12 meses fechados, do mais antigo para o mais novo."""

    total_investido: Decimal
    rendimento_total: Decimal
    acumulado_percentual: Decimal
    meses: list[RendimentoMes]
