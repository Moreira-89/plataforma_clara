"""
Router dos Blocos de Liquidez.

COMO FUNCIONA:
    1. `GET /blocos/etiquetas` devolve as pedras e as cores (qualquer perfil).
    2. `POST /blocos` cria um bloco: só a gestora, validado em `domain/blocos.py`.
    3. `GET /blocos` lista os blocos criados e `GET /blocos/{bloco_id}` devolve um bloco
       com as suas empresas; qualquer perfil autenticado. Os dois trazem o score de cada
       empresa e o do bloco (média ponderada pelo capital), lidos de `dados/scores_empresas.csv`.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    TokenInvalidoError: Sem token ou token inválido (401).
    AcessoNegadoError: Perfil diferente de gestora em `POST /blocos` (403).
    BlocoInvalidoError: Dados do bloco inválidos (422).
    EmpresaJaEmBlocoError: Empresa já pertence a outro bloco (409).
    BlocoNaoEncontradoError: Bloco inexistente em `GET /blocos/{bloco_id}` (404).
    DadosIndisponiveisError: Tabela de blocos fora do ar (503).
"""

import asyncio
from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, status

from app.api.dependencias import (
    BuscadorDeBloco,
    CriadorDeBloco,
    LeitorDeScores,
    ListadorDeBlocos,
    exigir_perfil,
    obter_buscador_de_bloco,
    obter_criador_de_bloco,
    obter_leitor_de_scores,
    obter_listador_de_blocos,
    obter_usuario_atual,
)
from app.api.mapeamento_blocos import listagem_do_bloco, risco
from app.api.schemas.auth import UsuarioAtual
from app.api.schemas.blocos import (
    BlocoCriado,
    BlocoDetalhe,
    BlocoListagem,
    EmpresaAlocadaResposta,
    EmpresaDoBlocoDetalhe,
    EtiquetaResposta,
    NovoBlocoRequisicao,
)
from app.domain.blocos import (
    ETIQUETAS,
    FUSO_BRASIL,
    AlocacaoEmpresa,
    montar_bloco,
)
from app.domain.perfis import Perfil

router = APIRouter(prefix="/blocos", tags=["blocos"], dependencies=[Depends(obter_usuario_atual)])


@router.get("/etiquetas", response_model=list[EtiquetaResposta])
async def listar_etiquetas() -> list[EtiquetaResposta]:
    """As pedras usadas como etiqueta, cada uma com a sua cor."""
    return [EtiquetaResposta(nome=nome, cor=cor) for nome, cor in ETIQUETAS.items()]


@router.post("", response_model=BlocoCriado, status_code=status.HTTP_201_CREATED)
async def criar_bloco(
    corpo: NovoBlocoRequisicao,
    gestora: Annotated[UsuarioAtual, Depends(exigir_perfil(Perfil.GESTORA))],
    criar: Annotated[CriadorDeBloco, Depends(obter_criador_de_bloco)],
) -> BlocoCriado:
    """Cria um bloco de liquidez. As porcentagens das empresas precisam somar 100%."""
    bloco = montar_bloco(
        corpo.etiqueta,
        corpo.capital_total,
        corpo.data_vencimento,
        corpo.responsavel_tecnico,
        corpo.observacao,
        [AlocacaoEmpresa(e.id_empresa, e.percentual_liquidez) for e in corpo.empresas],
        agora=datetime.now(FUSO_BRASIL),
        id_bloco=str(uuid4()),
    )
    await asyncio.to_thread(criar, bloco, gestora.uid)
    return BlocoCriado(
        id_bloco=bloco.id_bloco,
        codigo_identificacao=bloco.codigo_identificacao,
        etiqueta=bloco.etiqueta,
        capital_total=bloco.capital_total,
        data_criacao=bloco.data_criacao,
        data_vencimento=bloco.data_vencimento,
        empresas=[
            EmpresaAlocadaResposta(
                id_empresa=e.id_empresa,
                percentual_liquidez=e.percentual,
                capital_estimado=e.capital_estimado,
            )
            for e in bloco.empresas
        ],
    )


@router.get("", response_model=list[BlocoListagem])
async def listar_blocos(
    listar: Annotated[ListadorDeBlocos, Depends(obter_listador_de_blocos)],
    ler_scores: Annotated[LeitorDeScores, Depends(obter_leitor_de_scores)],
) -> list[BlocoListagem]:
    """Os blocos criados, do mais novo para o mais antigo, com o score de cada um."""
    blocos, scores = await asyncio.gather(asyncio.to_thread(listar), asyncio.to_thread(ler_scores))
    return [
        BlocoListagem(
            **listagem_do_bloco(
                b, [(p.id_empresa, p.capital_estimado) for p in b.participacoes], scores
            )
        )
        for b in blocos
    ]


@router.get("/{bloco_id}", response_model=BlocoDetalhe)
async def detalhar_bloco(
    bloco_id: str,
    buscar: Annotated[BuscadorDeBloco, Depends(obter_buscador_de_bloco)],
    ler_scores: Annotated[LeitorDeScores, Depends(obter_leitor_de_scores)],
) -> BlocoDetalhe:
    """Um bloco com as suas empresas, da maior para a menor fatia, cada uma com o seu score."""
    detalhado, scores = await asyncio.gather(
        asyncio.to_thread(buscar, bloco_id), asyncio.to_thread(ler_scores)
    )
    pares = [(e.id_empresa, e.capital_estimado) for e in detalhado.empresas]
    return BlocoDetalhe(
        **listagem_do_bloco(detalhado.bloco, pares, scores),
        empresas=[
            EmpresaDoBlocoDetalhe(**vars(e), **risco(scores.get(e.id_empresa)))
            for e in detalhado.empresas
        ],
    )
