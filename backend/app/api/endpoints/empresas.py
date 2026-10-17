"""
Router do cadastro de empresas.

COMO FUNCIONA:
    1. `GET /empresas?busca=` procura empresas por nome fantasia ou CNPJ.
    2. Só a gestora acessa: é a busca do formulário de criação de bloco.
    3. Cada empresa vem com o score e a nota de risco, para a gestora ver na busca.
    4. A consulta ao BigQuery roda em `asyncio.to_thread`.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    AcessoNegadoError: Perfil diferente de gestora (403).
    DadosIndisponiveisError: Cadastro de empresas fora do ar (503).
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencias import (
    BuscadorDeEmpresas,
    LeitorDeScores,
    exigir_perfil,
    obter_buscador_de_empresas,
    obter_leitor_de_scores,
)
from app.api.mapeamento_blocos import risco
from app.api.schemas.blocos import EmpresaBusca
from app.domain.perfis import Perfil

router = APIRouter(
    prefix="/empresas",
    tags=["empresas"],
    dependencies=[Depends(exigir_perfil(Perfil.GESTORA))],
)


@router.get("", response_model=list[EmpresaBusca])
async def buscar_empresas(
    busca: Annotated[str, Query(min_length=2, max_length=100)],
    buscar: Annotated[BuscadorDeEmpresas, Depends(obter_buscador_de_empresas)],
    ler_scores: Annotated[LeitorDeScores, Depends(obter_leitor_de_scores)],
) -> list[EmpresaBusca]:
    """Empresas livres (fora de qualquer bloco) cujo nome fantasia ou CNPJ contém o texto."""
    encontradas, scores = await asyncio.gather(
        asyncio.to_thread(buscar, busca), asyncio.to_thread(ler_scores)
    )
    return [EmpresaBusca(**vars(e), **risco(scores.get(e.id_empresa))) for e in encontradas]
