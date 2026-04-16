import logging
import time
from typing import Any

import pandas as pd
from google.cloud import bigquery

logger = logging.getLogger(__name__)

# ── Cache simples em memória com TTL ─────────────────────────────────────────
_cache_dados: list[dict[str, Any]] = []
_cache_timestamp: float = 0.0
_CACHE_TTL_SEGUNDOS: float = 300.0  # 5 minutos


def buscar_metricas_blocos_liquidez(*, force_refresh: bool = False) -> list[dict[str, Any]]:
    """
    Conecta no BigQuery e retorna um resumo financeiro e de risco
    agrupado por Bloco de Liquidez para alimentar os gráficos do Dashboard.

    Utiliza cache em memória com TTL de 5 minutos para evitar queries
    repetidas ao BigQuery a cada carregamento de página.

    Args:
        force_refresh: Se True, ignora o cache e busca dados frescos.

    Returns:
        Lista de dicts com as métricas por bloco de liquidez.
    """
    global _cache_dados, _cache_timestamp

    agora = time.monotonic()
    if not force_refresh and _cache_dados and (agora - _cache_timestamp) < _CACHE_TTL_SEGUNDOS:
        logger.debug("Retornando dados do cache (idade: %.1fs).", agora - _cache_timestamp)
        return _cache_dados

    try:
        client = bigquery.Client()

        query = """
            SELECT 
                bloco_liquidez_setorial,
                SUM(valor_mercado_atual) AS total_alocado,
                AVG(score_risco_interno) AS score_medio_reputacao,
                COUNT(id_aporte_uuid) AS quantidade_aportes
            FROM `plataforma-clara.dados_fidc.tb_aporte`
            WHERE bloco_liquidez_setorial IS NOT NULL
            GROUP BY bloco_liquidez_setorial
            ORDER BY total_alocado DESC
        """

        dataframe: pd.DataFrame = client.query(query).to_dataframe()

        # Preenche possíveis valores nulos com zero para não quebrar os gráficos
        dataframe = dataframe.fillna(0)

        dados_dashboard: list[dict[str, Any]] = dataframe.to_dict(orient="records")

        # Atualiza o cache
        _cache_dados = dados_dashboard
        _cache_timestamp = agora

        logger.info("Dados BigQuery carregados: %d blocos de liquidez.", len(dados_dashboard))
        return dados_dashboard

    except Exception as e:
        logger.error("Erro ao buscar métricas no BigQuery: %s", e, exc_info=True)
        return []