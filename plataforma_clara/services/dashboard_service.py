"""
Camada de serviço responsável pelas consultas analíticas no banco operacional.

Todas as funções utilizam o ORM/SQL do Reflex (SQLAlchemy por baixo) para consultar
a tabela `tb_aporte` no PostgreSQL (Supabase). Um cache em memória com TTL de 5 minutos
evita consultas repetidas durante a mesma sessão de uso.
"""

import logging
import time
from typing import Any

import sqlalchemy as sa
import reflex as rx

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# Cache em memória para reduzir consultas repetidas na mesma janela de uso.
# Estrutura: { cpf_investidor: (timestamp, lista_de_dados) }
_cache_investidor: dict[str, tuple[float, list[dict[str, Any]]]] = {}

# Cache para visão da gestora (sem filtro de investidor).
_cache_gestora: list[dict[str, Any]] = []
_cache_gestora_timestamp: float = 0.0

# TTL (Time-To-Live) do cache em segundos. Após 5 minutos, os dados são recarregados.
_CACHE_TTL_SEGUNDOS: float = 300.0


# -----------------------------------------------------------------------------
# CONSULTAS DO INVESTIDOR
# -----------------------------------------------------------------------------


def buscar_metricas_blocos_liquidez(
    *, cpf_investidor: str, force_refresh: bool = False
) -> list[dict[str, Any]]:
    """
    Busca um resumo financeiro e de risco agrupado por Bloco de Liquidez,
    filtrado pelo documento do investidor logado.

    COMO FUNCIONA:
        1. Verificação de Cache — Checa se há dados recentes para este CPF no cache
           em memória. Se sim e dentro do TTL, retorna imediatamente sem tocar o banco.
        2. Execução da Query — Consulta a tb_aporte via rx.session() agrupando por bloco,
           filtrando documentos apenas com dígitos (REGEXP_REPLACE).
        3. Atualização do Cache — Salva o resultado no cache com o timestamp atual.
        4. Retorno — Devolve a lista de dicts com as métricas por bloco.

    Args:
        cpf_investidor (str): CPF/CNPJ do investidor (somente dígitos) para filtro.
        force_refresh (bool): Se True, ignora o cache e busca dados frescos do banco.

    Returns:
        list[dict[str, Any]]: Lista de dicts com as métricas por bloco de liquidez.
                              Retorna lista vazia em caso de erro.
    """
    global _cache_investidor

    # --- 1. VERIFICAÇÃO DE CACHE ---
    agora = time.monotonic()
    if not force_refresh and cpf_investidor in _cache_investidor:
        ts, dados = _cache_investidor[cpf_investidor]
        if (agora - ts) < _CACHE_TTL_SEGUNDOS:
            logger.debug(
                "Cache hit para investidor %s (idade: %.1fs).", cpf_investidor, agora - ts
            )
            return dados

    # --- 2. EXECUÇÃO DA QUERY ---
    try:
        # REGEXP_REPLACE remove qualquer caractere não numérico antes de comparar,
        # garantindo que CPFs com ou sem formatação (ex: "123.456.789-00") sejam
        # tratados de forma uniforme.
        query = sa.text("""
            SELECT
                bloco_liquidez_setorial,
                SUM(valor_mercado_atual)      AS total_alocado,
                AVG(score_risco_interno)      AS score_medio_reputacao,
                COUNT(id_aporte_uuid)         AS quantidade_aportes
            FROM tb_aporte
            WHERE bloco_liquidez_setorial IS NOT NULL
              AND REGEXP_REPLACE(documento_investidor_cpf_cnpj, '[^0-9]', '', 'g') = :cpf_investidor
            GROUP BY bloco_liquidez_setorial
            ORDER BY total_alocado DESC
        """)

        with rx.session() as session:
            result = session.execute(query, {"cpf_investidor": cpf_investidor}).mappings().fetchall()

        dados_dashboard: list[dict[str, Any]] = [dict(row) for row in result]

        # --- 3. ATUALIZAÇÃO DO CACHE ---
        _cache_investidor[cpf_investidor] = (agora, dados_dashboard)

        logger.info(
            "Dados do investidor carregados: %d blocos para CPF=%s.",
            len(dados_dashboard),
            cpf_investidor,
        )
        # --- 4. RETORNO ---
        return dados_dashboard

    except Exception as exc:
        logger.error(
            "Erro ao buscar métricas para investidor %s: %s", cpf_investidor, exc, exc_info=True
        )
        return []


# -----------------------------------------------------------------------------
# CONSULTAS DA GESTORA
# -----------------------------------------------------------------------------


def buscar_metricas_gerais_gestora(*, force_refresh: bool = False) -> list[dict[str, Any]]:
    """
    Busca todos os dados agregados dos blocos, sem filtro de investidor (Visão Gestora).

    COMO FUNCIONA:
        1. Verificação de Cache — Usa um cache global (sem chave de CPF) com TTL de 5 min.
        2. Execução da Query — Agrega toda a tb_aporte por bloco de liquidez.
        3. Atualização do Cache — Persiste resultado e timestamp no cache global.
        4. Retorno — Lista de dicts com métricas de todos os blocos ativos.

    Args:
        force_refresh (bool): Se True, ignora o cache e recarrega do banco.

    Returns:
        list[dict[str, Any]]: Lista de métricas por bloco. Lista vazia em caso de erro.
    """
    global _cache_gestora, _cache_gestora_timestamp

    # --- 1. VERIFICAÇÃO DE CACHE ---
    agora = time.monotonic()
    if not force_refresh and _cache_gestora and (agora - _cache_gestora_timestamp) < _CACHE_TTL_SEGUNDOS:
        logger.debug("Cache hit para gestora (idade: %.1fs).", agora - _cache_gestora_timestamp)
        return _cache_gestora

    # --- 2. EXECUÇÃO DA QUERY ---
    try:
        query = sa.text("""
            SELECT
                bloco_liquidez_setorial,
                SUM(valor_mercado_atual)      AS total_alocado,
                AVG(score_risco_interno)      AS score_medio_reputacao,
                COUNT(id_aporte_uuid)         AS quantidade_aportes
            FROM tb_aporte
            WHERE bloco_liquidez_setorial IS NOT NULL
            GROUP BY bloco_liquidez_setorial
            ORDER BY total_alocado DESC
        """)

        with rx.session() as session:
            result = session.execute(query).mappings().fetchall()

        dados_dashboard: list[dict[str, Any]] = [dict(row) for row in result]

        # --- 3. ATUALIZAÇÃO DO CACHE ---
        _cache_gestora = dados_dashboard
        _cache_gestora_timestamp = agora

        logger.info("Dados da gestora carregados: %d blocos.", len(dados_dashboard))
        # --- 4. RETORNO ---
        return dados_dashboard

    except Exception as exc:
        logger.error("Erro ao buscar métricas da gestora: %s", exc, exc_info=True)
        return []


# -----------------------------------------------------------------------------
# TABELA DE APORTES (GESTORA)
# -----------------------------------------------------------------------------

# Cache específico para a tabela de aportes (ranking de empresas sacadas).
_cache_tabela_aportes: list[dict[str, Any]] = []
_cache_tabela_aportes_timestamp: float = 0.0


def buscar_tabela_aportes_gestora(*, force_refresh: bool = False) -> list[dict[str, Any]]:
    """
    Busca dados agregados por empresa sacada para a tabela de aportes da Gestora.

    Retorna empresa, CNPJ formatado, valor alocado, classificação de risco (derivada
    do score ML com escala A+ → C-) e status de adimplência.

    COMO FUNCIONA:
        1. Verificação de Cache — TTL de 5 minutos para a tabela de empresas.
        2. Execução da Query — Agrega tb_aporte por empresa/CNPJ, usando CASE WHEN
           para traduzir o score numérico em nota de crédito e status de adimplência.
        3. Formatação — Converte valores numéricos em strings no padrão brasileiro
           (R$ 1.234.567,89) e formata CNPJs com máscara (XX.XXX.XXX/XXXX-XX).
        4. Atualização do Cache e Retorno.

    Args:
        force_refresh (bool): Se True, ignora o cache e recarrega do banco.

    Returns:
        list[dict[str, Any]]: Lista de dicts com chaves: empresa, cnpj, valor, risco, status.
                              Retorna lista vazia em caso de erro.
    """
    global _cache_tabela_aportes, _cache_tabela_aportes_timestamp

    # --- 1. VERIFICAÇÃO DE CACHE ---
    agora = time.monotonic()
    if (
        not force_refresh
        and _cache_tabela_aportes
        and (agora - _cache_tabela_aportes_timestamp) < _CACHE_TTL_SEGUNDOS
    ):
        logger.debug(
            "Cache hit para tabela aportes gestora (idade: %.1fs).",
            agora - _cache_tabela_aportes_timestamp,
        )
        return _cache_tabela_aportes

    # --- 2. EXECUÇÃO DA QUERY ---
    try:
        query = sa.text("""
            SELECT
                empresa_sacada_nome,
                cnpj_sacado_limpo,
                SUM(valor_mercado_atual)  AS valor_total_alocado,
                AVG(score_risco_interno)  AS score_medio,
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

        # --- 3. FORMATAÇÃO ---

        def formatar_cnpj(cnpj: str) -> str:
            """Aplica a máscara XX.XXX.XXX/XXXX-XX ao CNPJ."""
            cnpj = str(cnpj).zfill(14)
            if len(cnpj) == 14 and cnpj.isdigit():
                return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
            return cnpj

        dados: list[dict[str, Any]] = []
        for row in dados_tabela:
            v = float(row["valor_total_alocado"]) if row["valor_total_alocado"] else 0.0
            # Converte para o padrão brasileiro: 1.234.567,89
            v_str = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            dados.append({
                "empresa": str(row["empresa_sacada_nome"]),
                "cnpj": formatar_cnpj(str(row["cnpj_sacado_limpo"])),
                "valor": f"R$ {v_str}",
                "risco": str(row["classificacao_risco"]),
                "status": str(row["status_atual"]),
            })

        # --- 4. ATUALIZAÇÃO DO CACHE E RETORNO ---
        _cache_tabela_aportes = dados
        _cache_tabela_aportes_timestamp = agora

        logger.info("Tabela de aportes da gestora carregada: %d registros.", len(dados))
        return dados

    except Exception as exc:
        logger.error("Erro ao buscar tabela de aportes da gestora: %s", exc, exc_info=True)
        return []
