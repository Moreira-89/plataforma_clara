"""
Router dos dashboards.

COMO FUNCIONA:
    1. `GET /dashboard/gestora` devolve a visão geral: mercado de FIDCs (CVM), rating, setores e blocos.
    2. Os dados vêm das views e tabelas do BigQuery (`storage/painel.py`), lidas em `asyncio.to_thread`.
    3. `GET /dashboard/investidor` segue respondendo 501 por falta da fonte dos aportes.
    4. Cada rota exige o seu perfil.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    AcessoNegadoError: Perfil errado para a rota (403).
    DadosIndisponiveisError: Views do BigQuery fora do ar (503).
    HTTPException: 501 no dashboard do investidor, depois da checagem de acesso.
"""

import asyncio
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencias import LeitorDoPainel, exigir_perfil, obter_leitor_do_painel
from app.api.erros import nao_implementado
from app.api.schemas.dashboard import (
    BlocoDoPainel,
    CapitalPorNota,
    DashboardGestora,
    DashboardInvestidor,
    EmpresaComAlerta,
    ExposicaoSetor,
    FaixaDeScore,
    FaixaRating,
    PontoMercado,
    ResumoBlocos,
    ResumoMercado,
    SetorBenchmark,
)
from app.domain.blocos import cor_da_etiqueta
from app.domain.painel import capital_por_nota, score_medio_ponderado
from app.domain.perfis import Perfil

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/gestora",
    response_model=DashboardGestora,
    dependencies=[Depends(exigir_perfil(Perfil.GESTORA))],
)
async def dashboard_gestora(
    ler: Annotated[LeitorDoPainel, Depends(obter_leitor_do_painel)],
) -> DashboardGestora:
    """Visão geral da gestora: mercado de FIDCs, rating, setores e blocos com score."""
    painel = await asyncio.to_thread(ler)
    return DashboardGestora(
        mercado=ResumoMercado(**asdict(painel.mercado)) if painel.mercado else None,
        serie_mercado=[PontoMercado(**asdict(p)) for p in painel.serie_mercado],
        rating=[FaixaRating(**asdict(f)) for f in painel.rating],
        setores=[SetorBenchmark(**asdict(s)) for s in painel.setores],
        resumo_blocos=ResumoBlocos(
            quantidade=len(painel.blocos),
            capital_total=sum(b.capital_total for b in painel.blocos),
            score_medio=score_medio_ponderado(painel.blocos),
        ),
        blocos=[
            BlocoDoPainel(**asdict(b), cor=cor_da_etiqueta(b.etiqueta)) for b in painel.blocos
        ],
        capital_por_nota=[CapitalPorNota(**asdict(c)) for c in capital_por_nota(painel.blocos)],
        exposicao=[ExposicaoSetor(**asdict(e)) for e in painel.exposicao],
        distribuicao_scores=[FaixaDeScore(**asdict(f)) for f in painel.distribuicao_scores],
        alertas=[EmpresaComAlerta(**asdict(a)) for a in painel.alertas],
    )


@router.get(
    "/investidor",
    response_model=DashboardInvestidor,
    dependencies=[Depends(exigir_perfil(Perfil.INVESTIDOR))],
)
async def dashboard_investidor() -> DashboardInvestidor:
    """Visão do investidor autenticado."""
    raise nao_implementado("fonte dos aportes e Firebase Auth")
