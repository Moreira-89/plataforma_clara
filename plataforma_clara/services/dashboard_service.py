import logging
import time
from typing import Any

import sqlalchemy as sa
import reflex as rx

logger = logging.getLogger(__name__)

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
        query = sa.text("""
            SELECT 
                bloco_liquidez_setorial,
                SUM(valor_mercado_atual) AS total_alocado,
                AVG(score_risco_interno) AS score_medio_reputacao,
                COUNT(id_aporte_uuid) AS quantidade_aportes
            FROM tb_aporte
            WHERE bloco_liquidez_setorial IS NOT NULL
              AND REGEXP_REPLACE(documento_investidor_cpf_cnpj, '[^0-9]', '', 'g') = :cpf_investidor
            GROUP BY bloco_liquidez_setorial
            ORDER BY total_alocado DESC
        """)

        with rx.session() as session:
            result = session.execute(query, {"cpf_investidor": cpf_investidor}).mappings().fetchall()
            
        dados_dashboard: list[dict[str, Any]] = [dict(row) for row in result]

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
        query = sa.text("""
            SELECT 
                bloco_liquidez_setorial,
                SUM(valor_mercado_atual) AS total_alocado,
                AVG(score_risco_interno) AS score_medio_reputacao,
                COUNT(id_aporte_uuid) AS quantidade_aportes
            FROM tb_aporte
            WHERE bloco_liquidez_setorial IS NOT NULL
            GROUP BY bloco_liquidez_setorial
            ORDER BY total_alocado DESC
        """)

        with rx.session() as session:
            result = session.execute(query).mappings().fetchall()
            
        dados_dashboard: list[dict[str, Any]] = [dict(row) for row in result]

        _cache_gestora = dados_dashboard
        _cache_gestora_timestamp = agora

        logger.info("Dados BigQuery gestora carregados: %d blocos.", len(dados_dashboard))
        return dados_dashboard

    except Exception as e:
        logger.error("Erro ao buscar métricas BigQuery para gestora: %s", e, exc_info=True)
        return []


# ── Cache para tabela de aportes da gestora ──────────────────────────────────
_cache_tabela_aportes: list[dict[str, Any]] = []
_cache_tabela_aportes_timestamp: float = 0.0


def buscar_tabela_aportes_gestora(*, force_refresh: bool = False) -> list[dict[str, Any]]:
    """
    Busca dados agregados por empresa sacada para a tabela de aportes da Gestora.

    Retorna empresa, CNPJ, valor alocado, classificação de risco (derivada do
    score ML) e status de adimplência (derivado do prazo de vencimento).

    Utiliza cache em memória com TTL de 5 minutos.
    """
    global _cache_tabela_aportes, _cache_tabela_aportes_timestamp

    agora = time.monotonic()
    if not force_refresh and _cache_tabela_aportes and (agora - _cache_tabela_aportes_timestamp) < _CACHE_TTL_SEGUNDOS:
        logger.debug("Cache hit para tabela aportes gestora (idade: %.1fs).", agora - _cache_tabela_aportes_timestamp)
        return _cache_tabela_aportes

    try:
        query = sa.text("""
            SELECT
                empresa_sacada_nome,
                cnpj_sacado_limpo,
                SUM(valor_mercado_atual) AS valor_total_alocado,
                AVG(score_risco_interno) AS score_medio,
                CASE
                    WHEN AVG(score_risco_interno) >= 80 THEN 'A+'
                    WHEN AVG(score_risco_interno) >= 70 THEN 'A'
                    WHEN AVG(score_risco_interno) >= 60 THEN 'A-'
                    WHEN AVG(score_risco_interno) >= 50 THEN 'B+'
                    WHEN AVG(score_risco_interno) >= 40 THEN 'B'
                    ELSE 'C-'
                END AS classificacao_risco,
                CASE
                    WHEN AVG(score_risco_interno) >= 60 THEN 'Adimplente'
                    WHEN AVG(score_risco_interno) >= 40 THEN 'Atenção'
                    ELSE 'Inadimplente'
                END AS status_atual
            FROM tb_aporte
            WHERE empresa_sacada_nome IS NOT NULL
            GROUP BY empresa_sacada_nome, cnpj_sacado_limpo
            ORDER BY valor_total_alocado DESC
            LIMIT 50
        """)

        with rx.session() as session:
            result = session.execute(query).mappings().fetchall()
            
        dados_tabela = [dict(row) for row in result]

        # Formata o CNPJ para exibição (XX.XXX.XXX/XXXX-XX)
        def formatar_cnpj(cnpj: str) -> str:
            cnpj = str(cnpj).zfill(14)
            if len(cnpj) == 14 and cnpj.isdigit():
                return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
            return cnpj

        dados: list[dict[str, Any]] = []
        for row in dados_tabela:
            v = float(row['valor_total_alocado']) if row['valor_total_alocado'] else 0.0
            v_str = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            dados.append({
                "empresa": str(row["empresa_sacada_nome"]),
                "cnpj": formatar_cnpj(str(row["cnpj_sacado_limpo"])),
                "valor": f"R$ {v_str}",
                "risco": str(row["classificacao_risco"]),
                "status": str(row["status_atual"]),
            })

        _cache_tabela_aportes = dados
        _cache_tabela_aportes_timestamp = agora

        logger.info("Tabela aportes gestora carregada: %d registros.", len(dados))
        return dados

    except Exception as e:
        logger.error("Erro ao buscar tabela de aportes para gestora: %s", e, exc_info=True)
        return []
