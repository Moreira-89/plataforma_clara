"""
Router dos investimentos do investidor.

Não há aporte real: a carteira de cada investidor é de demonstração (`domain/investimentos.py`),
sorteada de forma estável a partir do uid dele e dos blocos existentes.

COMO FUNCIONA:
    1. `GET /investimentos` lista os blocos em que o investidor logado "já investiu".
    2. Cada item traz os mesmos campos da lista de blocos (cor, score e nota) e o valor investido.
    3. Só o investidor acessa; a ordem é a da lista de blocos, do mais recente ao mais antigo.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    AcessoNegadoError: Perfil diferente de investidor (403).
    DadosIndisponiveisError: Tabela de blocos fora do ar (503).
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencias import (
    LeitorDeScores,
    ListadorDeBlocos,
    exigir_perfil,
    obter_leitor_de_scores,
    obter_listador_de_blocos,
)
from app.api.mapeamento_blocos import listagem_do_bloco
from app.api.schemas.auth import UsuarioAtual
from app.api.schemas.blocos import BlocoInvestido
from app.domain.investimentos import valor_investido
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
