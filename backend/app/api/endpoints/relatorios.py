"""
Router dos relatórios em PDF por IA.

COMO FUNCIONA:
    1. `POST /relatorios` carrega a carteira do investidor (a mesma fonte do cubo e do ranking),
       registra o pedido e gera o PDF em segundo plano, com `agents.relatorio` via `asyncio.to_thread`.
    2. `GET /relatorios/{id}` devolve o estado do pedido: `processando`, `pronto` ou `falhou`.
    3. `GET /relatorios/{id}/pdf` devolve o arquivo quando está pronto.
    4. Só o investidor acessa, e só os próprios pedidos. Um pedido em andamento não é duplicado.
    5. Os PDFs ficam em memória do processo (`storage/relatorios.py`) e somem ao reiniciar.

Args:
    Nenhum.

Returns:
    APIRouter: o `router` deste módulo.

Raises:
    AcessoNegadoError: Perfil diferente de investidor (403).
    SemInvestimentosError: Investidor sem blocos investidos (409).
    RelatorioNaoEncontradoError: Pedido inexistente ou de outro investidor (404).
    RelatorioNaoProntoError: PDF pedido antes de ficar pronto, ou de relatório que falhou (409).
    DadosIndisponiveisError: Tabela de blocos fora do ar (503).
"""

import asyncio
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response

from app.agents.relatorio import aportes_da_carteira
from app.api.carteira import carregar_carteira
from app.api.dependencias import (
    BuscadorDeBloco,
    GeradorDeRelatorio,
    LeitorDeHistorico,
    LeitorDeScores,
    ListadorDeBlocos,
    exigir_perfil,
    obter_buscador_de_bloco,
    obter_gerador_de_relatorio,
    obter_leitor_de_historico,
    obter_leitor_de_scores,
    obter_listador_de_blocos,
    obter_repositorio_de_relatorios,
)
from app.api.schemas.auth import UsuarioAtual
from app.api.schemas.relatorio import RelatorioStatus
from app.domain.erros import (
    RelatorioNaoEncontradoError,
    RelatorioNaoProntoError,
    SemInvestimentosError,
)
from app.domain.perfis import Perfil
from app.domain.relatorios import Relatorio, StatusRelatorio
from app.storage.relatorios import RepositorioDeRelatorios

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/relatorios", tags=["relatorios"])

MENSAGEM_DE_FALHA = "Não foi possível gerar o relatório agora. Tente de novo em instantes."

# Guarda as tarefas em andamento: o asyncio só mantém referência fraca a elas.
_tarefas: set[asyncio.Task] = set()


def _status(relatorio: Relatorio) -> RelatorioStatus:
    return RelatorioStatus(id=relatorio.id, status=relatorio.status, mensagem=relatorio.mensagem)


async def _gerar(
    repositorio: RepositorioDeRelatorios,
    gerar: GeradorDeRelatorio,
    relatorio: Relatorio,
    nome: str | None,
    aportes: list[dict[str, Any]],
) -> None:
    """Gera o PDF fora do loop e fecha o pedido como pronto ou falho."""
    try:
        pdf, arquivo = await asyncio.to_thread(gerar, nome, aportes)
    except Exception:
        logger.exception("Falha ao gerar o relatório %s.", relatorio.id)
        repositorio.falhar(relatorio.id, MENSAGEM_DE_FALHA)
        return
    repositorio.concluir(relatorio.id, pdf, arquivo)


@router.post("", response_model=RelatorioStatus)
async def pedir_relatorio(
    investidor: Annotated[UsuarioAtual, Depends(exigir_perfil(Perfil.INVESTIDOR))],
    listar: Annotated[ListadorDeBlocos, Depends(obter_listador_de_blocos)],
    buscar: Annotated[BuscadorDeBloco, Depends(obter_buscador_de_bloco)],
    ler_scores: Annotated[LeitorDeScores, Depends(obter_leitor_de_scores)],
    ler_historico: Annotated[LeitorDeHistorico, Depends(obter_leitor_de_historico)],
    repositorio: Annotated[RepositorioDeRelatorios, Depends(obter_repositorio_de_relatorios)],
    gerar: Annotated[GeradorDeRelatorio, Depends(obter_gerador_de_relatorio)],
) -> RelatorioStatus:
    """Pede o relatório consolidado do investidor autenticado; a geração segue em segundo plano."""
    if em_andamento := repositorio.em_andamento(investidor.uid):
        return _status(em_andamento)

    carteira, scores, historico = await asyncio.gather(
        carregar_carteira(investidor.uid, listar, buscar),
        asyncio.to_thread(ler_scores),
        asyncio.to_thread(ler_historico),
    )
    if not carteira:
        raise SemInvestimentosError("Você ainda não tem investimentos para gerar o relatório.")

    relatorio = repositorio.criar(investidor.uid)
    nome = investidor.nome or investidor.email
    aportes = aportes_da_carteira(carteira, scores, historico)
    tarefa = asyncio.create_task(_gerar(repositorio, gerar, relatorio, nome, aportes))
    _tarefas.add(tarefa)
    tarefa.add_done_callback(_tarefas.discard)
    return _status(relatorio)


def _do_investidor(
    relatorio_id: str, investidor: UsuarioAtual, repositorio: RepositorioDeRelatorios
) -> Relatorio:
    relatorio = repositorio.obter(relatorio_id, investidor.uid)
    if relatorio is None:
        raise RelatorioNaoEncontradoError("Relatório não encontrado.")
    return relatorio


@router.get("/{relatorio_id}", response_model=RelatorioStatus)
async def consultar_relatorio(
    relatorio_id: str,
    investidor: Annotated[UsuarioAtual, Depends(exigir_perfil(Perfil.INVESTIDOR))],
    repositorio: Annotated[RepositorioDeRelatorios, Depends(obter_repositorio_de_relatorios)],
) -> RelatorioStatus:
    """Estado de um relatório pedido."""
    return _status(_do_investidor(relatorio_id, investidor, repositorio))


@router.get(
    "/{relatorio_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def baixar_relatorio(
    relatorio_id: str,
    investidor: Annotated[UsuarioAtual, Depends(exigir_perfil(Perfil.INVESTIDOR))],
    repositorio: Annotated[RepositorioDeRelatorios, Depends(obter_repositorio_de_relatorios)],
) -> Response:
    """O PDF do relatório, quando pronto."""
    relatorio = _do_investidor(relatorio_id, investidor, repositorio)
    if relatorio.status != StatusRelatorio.PRONTO or relatorio.pdf is None:
        raise RelatorioNaoProntoError("O relatório ainda não está pronto.")
    return Response(
        content=relatorio.pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{relatorio.arquivo}"'},
    )
