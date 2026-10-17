"""
Router dos investimentos do investidor.

Não há aporte real: a carteira de cada investidor é de demonstração (`domain/investimentos.py`),
sorteada de forma estável a partir do uid dele e dos blocos existentes.

COMO FUNCIONA:
    1. `GET /investimentos` lista os blocos em que o investidor logado "já investiu".
    2. Cada item traz os mesmos campos da lista de blocos (cor, score e nota) e o valor investido.
    3. `GET /investimentos/resumo` soma a carteira por etiqueta e devolve o total investido.
    4. `GET /investimentos/empresas` ranqueia as empresas da carteira pelo capital do investidor.
    5. Só o investidor acessa; a lista segue a ordem dos blocos, do mais recente ao mais antigo.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    AcessoNegadoError: Perfil diferente de investidor (403).
    DadosIndisponiveisError: Tabela de blocos fora do ar (503).
"""

import asyncio
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.carteira import carregar_carteira
from app.api.dependencias import (
    BuscadorDeBloco,
    LeitorDeScores,
    ListadorDeBlocos,
    exigir_perfil,
    obter_buscador_de_bloco,
    obter_leitor_de_scores,
    obter_listador_de_blocos,
)
from app.api.mapeamento_blocos import listagem_do_bloco, risco
from app.api.schemas.auth import UsuarioAtual
from app.api.schemas.blocos import BlocoInvestido
from app.api.schemas.investimentos import EmpresaDaCarteira, ResumoEtiqueta, ResumoInvestimentos
from app.domain.blocos import cor_da_etiqueta
from app.domain.investimentos import ranquear_empresas, resumir_por_etiqueta, valor_investido
from app.domain.perfis import Perfil

router = APIRouter(prefix="/investimentos", tags=["investimentos"])


@router.get("", response_model=list[BlocoInvestido])
async def listar_investimentos(
    investidor: Annotated[UsuarioAtual, Depends(exigir_perfil(Perfil.INVESTIDOR))],
    listar: Annotated[ListadorDeBlocos, Depends(obter_listador_de_blocos)],
    ler_scores: Annotated[LeitorDeScores, Depends(obter_leitor_de_scores)],
) -> list[BlocoInvestido]:
    """Os blocos em que o investidor logado já investiu, com o valor de cada um."""
    blocos, scores = await asyncio.gather(asyncio.to_thread(listar), asyncio.to_thread(ler_scores))
    carteira = []
    for bloco in blocos:
        valor = valor_investido(investidor.uid, bloco.id_bloco)
        if valor is None:
            continue
        pares = [(p.id_empresa, p.capital_estimado) for p in bloco.participacoes]
        carteira.append(
            BlocoInvestido(**listagem_do_bloco(bloco, pares, scores), valor_investido=valor)
        )
    return carteira


@router.get("/resumo", response_model=ResumoInvestimentos)
async def resumir_investimentos(
    investidor: Annotated[UsuarioAtual, Depends(exigir_perfil(Perfil.INVESTIDOR))],
    listar: Annotated[ListadorDeBlocos, Depends(obter_listador_de_blocos)],
) -> ResumoInvestimentos:
    """O total investido e a soma por etiqueta, da maior para a menor."""
    blocos = await asyncio.to_thread(listar)
    investimentos = [
        (bloco.etiqueta, valor)
        for bloco in blocos
        if (valor := valor_investido(investidor.uid, bloco.id_bloco)) is not None
    ]
    etiquetas = [
        ResumoEtiqueta(**vars(resumo), cor=cor_da_etiqueta(resumo.etiqueta))
        for resumo in resumir_por_etiqueta(investimentos)
    ]
    return ResumoInvestimentos(
        total_investido=sum((e.total_investido for e in etiquetas), Decimal(0)),
        etiquetas=etiquetas,
    )


@router.get("/empresas", response_model=list[EmpresaDaCarteira])
async def ranquear_empresas_da_carteira(
    investidor: Annotated[UsuarioAtual, Depends(exigir_perfil(Perfil.INVESTIDOR))],
    listar: Annotated[ListadorDeBlocos, Depends(obter_listador_de_blocos)],
    buscar: Annotated[BuscadorDeBloco, Depends(obter_buscador_de_bloco)],
    ler_scores: Annotated[LeitorDeScores, Depends(obter_leitor_de_scores)],
) -> list[EmpresaDaCarteira]:
    """As empresas da carteira, da que mais recebe do dinheiro do investidor para a que menos."""
    carteira, scores = await asyncio.gather(
        carregar_carteira(investidor.uid, listar, buscar), asyncio.to_thread(ler_scores)
    )
    ranking = ranquear_empresas(carteira)
    return [
        EmpresaDaCarteira(
            **vars(empresa),
            cor=cor_da_etiqueta(empresa.etiqueta),
            **risco(scores.get(empresa.id_empresa)),
        )
        for empresa in ranking
    ]
