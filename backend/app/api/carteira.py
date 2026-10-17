"""
Carteira do investidor: os blocos em que ele investiu, com o valor e as empresas de cada um.

É a mesma fonte que alimenta o ranking e o cubo da visão geral e que serve de dado ao relatório.

COMO FUNCIONA:
    1. Lista os blocos e fica com os que a carteira de demonstração do investidor inclui.
    2. Busca o detalhe de cada um (empresas, fatias e capital), em paralelo.
    3. Devolve pares (valor investido, bloco detalhado), na ordem da lista de blocos.

Args:
    uid (str): Uid do investidor.
    listar (ListadorDeBlocos): Função que lista os blocos.
    buscar (BuscadorDeBloco): Função que busca um bloco com as suas empresas.

Returns:
    list[tuple[Decimal, BlocoDetalhado]]: A carteira; vazia se o investidor não tem blocos.

Raises:
    DadosIndisponiveisError: Tabela de blocos fora do ar.
"""

import asyncio
from decimal import Decimal

from app.api.dependencias import BuscadorDeBloco, ListadorDeBlocos
from app.domain.blocos import BlocoDetalhado
from app.domain.investimentos import valor_investido


async def carregar_carteira(
    uid: str, listar: ListadorDeBlocos, buscar: BuscadorDeBloco
) -> list[tuple[Decimal, BlocoDetalhado]]:
    """Os blocos investidos pelo uid, com o valor investido e o detalhe de cada um."""
    blocos = await asyncio.to_thread(listar)
    investidos = [
        (valor, bloco.id_bloco)
        for bloco in blocos
        if (valor := valor_investido(uid, bloco.id_bloco)) is not None
    ]
    detalhados = await asyncio.gather(
        *(asyncio.to_thread(buscar, id_bloco) for _, id_bloco in investidos)
    )
    return list(zip((valor for valor, _ in investidos), detalhados, strict=True))
