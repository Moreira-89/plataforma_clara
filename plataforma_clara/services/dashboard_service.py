"""
Serviço de consultas analíticas dos dashboards.

Depois da extração do domínio, este módulo faz três coisas e só essas: decide o
escopo da sessão de banco, aplica o cache e traduz falha de infraestrutura em
resposta vazia. O SQL foi para `infra/repositorios/aporte.py` e a formatação para
`domain/metricas.py`.

A sessão entra por injeção: cada função recebe uma FÁBRICA de sessão, não uma
sessão pronta. É o que permite devolver dado cacheado sem abrir conexão com o
banco — e o que faz os testes rodarem sem Postgres nenhum.

O cache é em memória e por processo. Com múltiplos workers Uvicorn, cada um terá o
seu (D4 no roadmap); a Fase 3 troca esta classe por Redis sem tocar no resto.
"""

import logging
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from sqlmodel import Session

from plataforma_clara.domain import metricas
from plataforma_clara.domain.schemas import (
    LinhaTabelaGestora,
    LinhaTransparencia,
    MetricaBloco,
)
from plataforma_clara.infra.db import sessao as sessao_padrao
from plataforma_clara.infra.repositorios.aporte import AporteRepositorio

logger = logging.getLogger(__name__)

# Tipo da fábrica de sessão: qualquer coisa que, chamada, devolva um gerenciador
# de contexto de Session. `infra.db.sessao` é a implementação real; os testes
# passam um substituto.
FabricaDeSessao = Callable[[], AbstractContextManager[Session]]

# TTL do cache em segundos. Após 5 minutos, os dados são recarregados do banco.
_CACHE_TTL_SEGUNDOS: float = 300.0


# -----------------------------------------------------------------------------
# CACHE EM MEMÓRIA
# -----------------------------------------------------------------------------


class _CacheComTTL:
    """
    Cache simples de processo, com expiração por tempo.

    Substitui os cinco globais de módulo que existiam antes (um par
    valor/timestamp para cada consulta). Usa `time.monotonic`, que nunca anda para
    trás — um ajuste de relógio do sistema não faz o cache expirar cedo demais nem
    tarde demais.
    """

    def __init__(self, ttl_segundos: float) -> None:
        self.ttl_segundos = ttl_segundos
        self._entradas: dict[str, tuple[float, Any]] = {}

    def obter(self, chave: str) -> Any | None:
        """Devolve o valor guardado se ainda estiver dentro do TTL, senão None."""
        entrada = self._entradas.get(chave)
        if entrada is None:
            return None

        gravado_em, valor = entrada
        idade = time.monotonic() - gravado_em
        if idade >= self.ttl_segundos:
            return None

        logger.debug("Cache hit para '%s' (idade: %.1fs).", chave, idade)
        return valor

    def guardar(self, chave: str, valor: Any) -> None:
        """Guarda o valor com o instante atual."""
        self._entradas[chave] = (time.monotonic(), valor)

    def limpar(self) -> None:
        """
        Descarta tudo.

        Hoje só os testes chamam. O gancho natural é invalidar o cache logo após
        uma ingestão bem-sucedida — sem isso, a gestora que acaba de subir um CSV
        continua vendo os números antigos por até cinco minutos, a menos que a tela
        peça `force_refresh`. Ligar isso é mudança de comportamento e ficou de fora
        desta fase de propósito; na Fase 3 vira um consumidor de evento.
        """
        self._entradas.clear()


_cache = _CacheComTTL(_CACHE_TTL_SEGUNDOS)


# -----------------------------------------------------------------------------
# CONSULTAS
# -----------------------------------------------------------------------------


def _consultar_com_cache(
    chave: str,
    consulta: Callable[[AporteRepositorio], Any],
    *,
    force_refresh: bool,
    sessao_factory: FabricaDeSessao,
    vazio: Any,
) -> Any:
    """
    Executa uma consulta com cache e tratamento de falha padronizados.

    COMO FUNCIONA:
        1. Cache — Fora do `force_refresh`, um valor válido é devolvido sem abrir
           conexão com o banco.
        2. Consulta — Abre a sessão, monta o repositório e executa.
        3. Gravação — Só um resultado bem-sucedido entra no cache. Uma falha NÃO é
           cacheada: fosse cacheada, uma indisponibilidade de segundos esconderia
           os dados por cinco minutos.
        4. Falha — A exceção é registrada e engolida, devolvendo o valor vazio.

    CARACTERIZAÇÃO DE COMPORTAMENTO DISCUTÍVEL: para quem está na tela, banco fora
    do ar é indistinguível de "não há aportes" — aparecem zeros, não um aviso de
    erro. Na Fase 2 isso deve virar um 5xx explícito no endpoint.

    Args:
        chave (str): Chave de cache da consulta.
        consulta (Callable): Recebe o repositório e devolve o resultado.
        force_refresh (bool): Ignora o cache quando True.
        sessao_factory (FabricaDeSessao): De onde vem a sessão de banco.
        vazio (Any): O que devolver em caso de falha.

    Returns:
        Any: O resultado da consulta, o valor cacheado, ou `vazio` em caso de falha.
    """
    # --- 1. CACHE ---
    if not force_refresh:
        cacheado = _cache.obter(chave)
        if cacheado is not None:
            return cacheado

    try:
        # --- 2. CONSULTA ---
        with sessao_factory() as sessao:
            resultado = consulta(AporteRepositorio(sessao))

        # --- 3. GRAVAÇÃO ---
        _cache.guardar(chave, resultado)
        return resultado

    except Exception as exc:
        # --- 4. FALHA ---
        logger.error("Falha na consulta '%s': %s", chave, exc, exc_info=True)
        return vazio


def buscar_metricas_blocos_liquidez(
    *,
    documento_investidor: str,
    force_refresh: bool = False,
    sessao_factory: FabricaDeSessao = sessao_padrao,
) -> list[MetricaBloco]:
    """
    Busca as métricas por Bloco de Liquidez da carteira de um investidor.

    Args:
        documento_investidor (str): CPF/CNPJ do investidor, somente com dígitos.
        force_refresh (bool): Ignora o cache — usar após uma ingestão.
        sessao_factory (FabricaDeSessao): Fábrica de sessão de banco.

    Returns:
        list[MetricaBloco]: Blocos do investidor. Lista vazia em caso de falha.
    """
    return _consultar_com_cache(
        f"blocos_investidor:{documento_investidor}",
        lambda repositorio: repositorio.metricas_por_bloco(
            documento_investidor=documento_investidor
        ),
        force_refresh=force_refresh,
        sessao_factory=sessao_factory,
        vazio=[],
    )


def buscar_metricas_gerais_gestora(
    *,
    force_refresh: bool = False,
    sessao_factory: FabricaDeSessao = sessao_padrao,
) -> list[MetricaBloco]:
    """
    Busca as métricas por Bloco de Liquidez de toda a carteira (visão da gestora).

    Args:
        force_refresh (bool): Ignora o cache.
        sessao_factory (FabricaDeSessao): Fábrica de sessão de banco.

    Returns:
        list[MetricaBloco]: Todos os blocos. Lista vazia em caso de falha.
    """
    return _consultar_com_cache(
        "blocos_gestora",
        lambda repositorio: repositorio.metricas_por_bloco(),
        force_refresh=force_refresh,
        sessao_factory=sessao_factory,
        vazio=[],
    )


def buscar_tabela_aportes_gestora(
    *,
    force_refresh: bool = False,
    sessao_factory: FabricaDeSessao = sessao_padrao,
) -> list[LinhaTabelaGestora]:
    """
    Busca a tabela de empresas sacadas do dashboard da gestora.

    A classificação de risco e o status de adimplência, que antes vinham de um
    `CASE WHEN` na query, agora são calculados em `domain/metricas.py` sobre o
    score médio devolvido pelo banco. As faixas são as mesmas.

    Args:
        force_refresh (bool): Ignora o cache.
        sessao_factory (FabricaDeSessao): Fábrica de sessão de banco.

    Returns:
        list[LinhaTabelaGestora]: Até 50 empresas, já formatadas. Vazia em falha.
    """
    return _consultar_com_cache(
        "tabela_gestora",
        lambda repositorio: metricas.montar_tabela_gestora(repositorio.empresas_sacadas()),
        force_refresh=force_refresh,
        sessao_factory=sessao_factory,
        vazio=[],
    )


def buscar_tabela_transparencia_investidor(
    *,
    documento_investidor: str,
    sessao_factory: FabricaDeSessao = sessao_padrao,
) -> list[LinhaTransparencia]:
    """
    Busca a tabela de transparência do investidor (empresas por bloco).

    Sem cache, por simetria com o comportamento anterior — esta consulta era feita
    direto no state, a cada carregamento do dashboard.

    Args:
        documento_investidor (str): CPF/CNPJ do investidor, somente com dígitos.
        sessao_factory (FabricaDeSessao): Fábrica de sessão de banco.

    Returns:
        list[LinhaTransparencia]: Linhas formatadas. Lista vazia em caso de falha.
    """
    try:
        with sessao_factory() as sessao:
            agregados = AporteRepositorio(sessao).empresas_por_bloco_do_investidor(
                documento_investidor
            )
    except Exception as exc:
        logger.error("Falha ao buscar tabela de transparência: %s", exc, exc_info=True)
        return []

    return metricas.montar_tabela_transparencia(agregados)


def buscar_patrimonio_total(
    *, sessao_factory: FabricaDeSessao = sessao_padrao
) -> float:
    """
    Soma o valor de mercado de todos os aportes sob gestão.

    Args:
        sessao_factory (FabricaDeSessao): Fábrica de sessão de banco.

    Returns:
        float: Patrimônio total. Zero em caso de falha.
    """
    try:
        with sessao_factory() as sessao:
            return AporteRepositorio(sessao).patrimonio_total()
    except Exception as exc:
        logger.error("Falha ao buscar patrimônio total: %s", exc, exc_info=True)
        return 0.0
