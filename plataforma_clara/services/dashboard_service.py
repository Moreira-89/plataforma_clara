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


def buscar_metricas_blocos_liquidez(*, force_refresh: bool = False, investidor_id: str) -> list[dict[str, Any]]:
    """
    Conecta no BigQuery e retorna um resumo financeiro e de risco
    agrupado por Bloco de Liquidez para alimentar os gráficos do Dashboard.

    Utiliza cache em memória com TTL de 5 minutos para evitar queries
    repetidas ao BigQuery a cada carregamento de página.

    Filtra investidos pelo id do investidor

    Args:
        force_refresh: Se True, ignora o cache e busca dados frescos.
        investidor_id: ID do investidor para filtrar os dados.

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
                SUM(valor_mercado_atual) as total_alocado,
                AVG(score_risco_interno) as score_medio_reputacao,
                COUNT(id_aporte_uuid) as quantidade_aportes
            FROM `seu-projeto.seu_dataset.tb_aporte`
            WHERE bloco_liquidez_setorial IS NOT NULL
              AND investidor_id = @investidor_id
            GROUP BY bloco_liquidez_setorial
            ORDER BY total_alocado DESC
        """

        # 3. Configuração do parâmetro do BigQuery ligando a variável Python ao SQL
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("investidor_id", "STRING", investidor_id)
            ]
        )
        
        # 4. Execução da query injetando a configuração
        dataframe = client.query(query, job_config=job_config).to_dataframe()
        
        dataframe.fillna(0, inplace=True)
        dados_dashboard = dataframe.to_dict(orient="records")
        
        return dados_dashboard
        
    except Exception as e:
        print(f"Erro ao buscar métricas no BigQuery para o ID {investidor_id}: {e}")
        return []