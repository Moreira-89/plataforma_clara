"""
Router dos Blocos de Liquidez.

COMO FUNCIONA:
    1. `GET /blocos/etiquetas` devolve as pedras e as cores (qualquer perfil).
    2. `POST /blocos` cria um bloco: só a gestora, validado em `domain/blocos.py`.
    3. `GET /blocos` lista os blocos criados e `GET /blocos/{bloco_id}` devolve um bloco
       com as suas empresas; qualquer perfil autenticado.

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
    ListadorDeBlocos,
    exigir_perfil,
    obter_buscador_de_bloco,
    obter_criador_de_bloco,
    obter_listador_de_blocos,
    obter_usuario_atual,
)
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
    BlocoListado,
    cor_da_etiqueta,
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


def _listagem(bloco: BlocoListado) -> dict:
    return {**vars(bloco), "cor": cor_da_etiqueta(bloco.etiqueta)}


@router.get("", response_model=list[BlocoListagem])
async def listar_blocos(
    listar: Annotated[ListadorDeBlocos, Depends(obter_listador_de_blocos)],
) -> list[BlocoListagem]:
    """Os blocos criados, do mais novo para o mais antigo."""
    blocos = await asyncio.to_thread(listar)
    return [BlocoListagem(**_listagem(b)) for b in blocos]


@router.get("/{bloco_id}", response_model=BlocoDetalhe)
async def detalhar_bloco(
    bloco_id: str,
    buscar: Annotated[BuscadorDeBloco, Depends(obter_buscador_de_bloco)],
) -> BlocoDetalhe:
    """Um bloco com as suas empresas, da maior para a menor fatia."""
    detalhado = await asyncio.to_thread(buscar, bloco_id)
    return BlocoDetalhe(
        **_listagem(detalhado.bloco),
        empresas=[EmpresaDoBlocoDetalhe(**vars(e)) for e in detalhado.empresas],
    )
