import logging
import os
import time
from typing import Any

import pandas as pd
from google.cloud import bigquery

logger = logging.getLogger(__name__)

# ── Constantes ───────────────────────────────────────────────────────────────
_TABLE_ID = os.getenv("TB_APORTE_ID", "plataforma-clara.dados_fidc.tb_aporte")

# ── Cache simples em memória com TTL ─────────────────────────────────────────
_cache_investidor: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_cache_gestora: list[dict[str, Any]] = []
_cache_gestora_timestamp: float = 0.0
_CACHE_TTL_SEGUNDOS: float = 300.0  # 5 minutos


def buscar_metricas_blocos_liquidez(
    *, cpf_investidor: str, force_refresh: bool = False
) -> list[dict[str, Any]]:
    """
    Conecta no BigQuery e retorna um resumo financeiro e de risco
    agrupado por Bloco de Liquidez, filtrado pelo documento do investidor.

    Utiliza cache em memória por investidor com TTL de 5 minutos.

    Args:
        cpf_investidor: Documento do investidor para filtrar os dados.
        force_refresh: Se True, ignora o cache e busca dados frescos.

    Returns:
        Lista de dicts com as métricas por bloco de liquidez.
    """
    global _cache_investidor

    agora = time.monotonic()

    # Verifica cache por investidor
    if not force_refresh and cpf_investidor in _cache_investidor:
        ts, dados = _cache_investidor[cpf_investidor]
        if (agora - ts) < _CACHE_TTL_SEGUNDOS:
            logger.debug("Cache hit para investidor %s (idade: %.1fs).", cpf_investidor, agora - ts)
            return dados

    try:
        client = bigquery.Client()

        query = f"""
            SELECT 
                bloco_liquidez_setorial,
                SUM(valor_mercado_atual) AS total_alocado,
                AVG(score_risco_interno) AS score_medio_reputacao,
                COUNT(id_aporte_uuid) AS quantidade_aportes
            FROM `{_TABLE_ID}`
            WHERE bloco_liquidez_setorial IS NOT NULL
              AND documento_investidor_cpf_cnpj = @cpf_investidor
            GROUP BY bloco_liquidez_setorial
            ORDER BY total_alocado DESC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("cpf_investidor", "STRING", cpf_investidor)
            ]
        )

        dataframe: pd.DataFrame = client.query(query, job_config=job_config).to_dataframe()
        dataframe = dataframe.fillna(0)
        dados_dashboard: list[dict[str, Any]] = dataframe.to_dict(orient="records")

        # Atualiza cache deste investidor
        _cache_investidor[cpf_investidor] = (agora, dados_dashboard)

        logger.info(
            "Dados BigQuery investidor carregados: %d blocos para %s.",
            len(dados_dashboard),
            cpf_investidor,
        )
        return dados_dashboard

    except Exception as e:
        logger.error("Erro ao buscar métricas no BigQuery para %s: %s", cpf_investidor, e, exc_info=True)
        return []


def buscar_metricas_gerais_gestora(*, force_refresh: bool = False) -> list[dict[str, Any]]:
    """
    Busca todos os dados agregados dos blocos, sem filtro de CPF (Visão Gestora).

    Utiliza cache em memória com TTL de 5 minutos.

    Args:
        force_refresh: Se True, ignora o cache e busca dados frescos.

    Returns:
        Lista de dicts com as métricas por bloco de liquidez.
    """
    global _cache_gestora, _cache_gestora_timestamp

    agora = time.monotonic()
    if not force_refresh and _cache_gestora and (agora - _cache_gestora_timestamp) < _CACHE_TTL_SEGUNDOS:
        logger.debug("Cache hit para gestora (idade: %.1fs).", agora - _cache_gestora_timestamp)
        return _cache_gestora

    try:
        client = bigquery.Client()

        query = f"""
            SELECT 
                bloco_liquidez_setorial,
                SUM(valor_mercado_atual) AS total_alocado,
                AVG(score_risco_interno) AS score_medio_reputacao,
                COUNT(id_aporte_uuid) AS quantidade_aportes
            FROM `{_TABLE_ID}`
            WHERE bloco_liquidez_setorial IS NOT NULL
            GROUP BY bloco_liquidez_setorial
            ORDER BY total_alocado DESC
        """

        dataframe: pd.DataFrame = client.query(query).to_dataframe()
        dataframe = dataframe.fillna(0)
        dados_dashboard: list[dict[str, Any]] = dataframe.to_dict(orient="records")

        _cache_gestora = dados_dashboard
        _cache_gestora_timestamp = agora

        logger.info("Dados BigQuery gestora carregados: %d blocos.", len(dados_dashboard))
        return dados_dashboard

    except Exception as e:
        logger.error("Erro ao buscar métricas BigQuery para gestora: %s", e, exc_info=True)
        return []