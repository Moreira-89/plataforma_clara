"""
Leitura dos dados do painel da gestora no BigQuery (dataset `BIGQUERY_DATASET_EMPRESAS`).

COMO FUNCIONA:
    1. Consulta as views do mercado de FIDCs (resumo, série mensal, rating e setores) e a dos blocos.
    2. As cinco consultas rodam em paralelo; rating e setores pegam só o mês mais recente.
    3. Taxas e participações saem em porcentagem, pelas funções de `domain/painel.py`.

Args:
    Nenhum.

Returns:
    PainelDaGestora: via `carregar_painel()`.

Raises:
    DadosIndisponiveisError: View inexistente, sem permissão ou consulta que falhou.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

from google.api_core.exceptions import Forbidden, GoogleAPICallError, NotFound

from app.config.settings import settings
from app.domain import painel as regras
from app.domain.erros import DadosIndisponiveisError
from app.storage.bigquery import cliente_compartilhado, tabela

logger = logging.getLogger(__name__)

_DATASET = settings.bigquery_dataset_empresas


def _linhas(sql: str) -> list:
    return list(cliente_compartilhado().query(sql).result())


def _mercado() -> regras.ResumoMercado | None:
    linhas = _linhas(f"SELECT * FROM {tabela('vw_cvm_mercado_resumo', _DATASET)} LIMIT 1")
    if not linhas:
        return None
    r = linhas[0]
    inadimplencia = regras.para_percentual(r.TX_INADIMPLENCIA)
    anterior = regras.para_percentual(r.TX_INAD_MES_ANTERIOR)
    return regras.ResumoMercado(
        referencia=r.DT_REFERENCIA,
        fundos_ativos=r.QTD_FUNDOS_ATIVOS,
        pl_total=float(r.VL_PL_TOTAL),
        var_pl_mes=regras.para_percentual(r.VAR_PL_MES_ANTERIOR),
        inadimplencia=inadimplencia,
        var_inadimplencia_pp=regras.diferenca_em_pontos(inadimplencia, anterior),
        inadimplencia_acima_90=regras.para_percentual(r.PCT_INAD_ACIMA_90_DIAS),
    )


def _inadimplencia() -> list[regras.PontoInadimplencia]:
    sql = f"""
        SELECT DT_COMPETENCIA, TX_INADIMPLENCIA
        FROM {tabela("vw_cvm_mercado_mensal", _DATASET)}
        ORDER BY DT_COMPETENCIA
    """
    return [
        regras.PontoInadimplencia(r.DT_COMPETENCIA, regras.para_percentual(r.TX_INADIMPLENCIA))
        for r in _linhas(sql)
    ]


def _rating() -> list[regras.FaixaRating]:
    view = tabela("vw_cvm_rating_mensal", _DATASET)
    sql = f"""
        SELECT NOTA_SCR, PCT_CARTEIRA, VL_CARTEIRA
        FROM {view}
        WHERE DT_COMPETENCIA = (SELECT MAX(DT_COMPETENCIA) FROM {view})
    """
    faixas = [
        regras.FaixaRating(r.NOTA_SCR, regras.para_percentual(r.PCT_CARTEIRA), float(r.VL_CARTEIRA))
        for r in _linhas(sql)
    ]
    return regras.ordenar_rating(faixas)


def _setores() -> list[regras.SetorBenchmark]:
    view = tabela("vw_cvm_benchmark_setor", _DATASET)
    sql = f"""
        SELECT SETOR, PCT_MERCADO, TX_INAD_AGREGADA_CONCENTRADOS
        FROM {view}
        WHERE DT_COMPETENCIA = (SELECT MAX(DT_COMPETENCIA) FROM {view})
        ORDER BY PCT_MERCADO DESC
    """
    return [
        regras.SetorBenchmark(
            r.SETOR,
            regras.para_percentual(r.PCT_MERCADO),
            regras.para_percentual(r.TX_INAD_AGREGADA_CONCENTRADOS),
        )
        for r in _linhas(sql)
    ]


def _blocos() -> list[regras.BlocoDoPainel]:
    sql = f"""
        SELECT id_bloco, codigo_identificacao, etiqueta, capital_total, QTD_EMPRESAS,
               SCORE_BLOCO, NOTA_BLOCO, SETORES_CVM
        FROM {tabela("vw_blocos_score", _DATASET)}
        ORDER BY SCORE_BLOCO DESC
    """
    return [
        regras.BlocoDoPainel(
            id_bloco=r.id_bloco,
            codigo=r.codigo_identificacao,
            etiqueta=r.etiqueta,
            capital_total=float(r.capital_total),
            qtd_empresas=r.QTD_EMPRESAS,
            score=None if r.SCORE_BLOCO is None else float(r.SCORE_BLOCO),
            nota=r.NOTA_BLOCO,
            setores=[s.strip() for s in (r.SETORES_CVM or "").split(",") if s.strip()],
        )
        for r in _linhas(sql)
    ]


def carregar_painel() -> regras.PainelDaGestora:
    """
    Lê do BigQuery tudo o que a visão geral da gestora desenha. Bloqueante.

    Returns:
        PainelDaGestora: Mercado, série de inadimplência, rating, setores e blocos.

    Raises:
        DadosIndisponiveisError: View inexistente, sem permissão ou consulta que falhou.
    """
    try:
        with ThreadPoolExecutor(max_workers=5) as pool:
            tarefas = [pool.submit(f) for f in (_mercado, _inadimplencia, _rating, _setores, _blocos)]
            mercado, inadimplencia, rating, setores, blocos = (t.result() for t in tarefas)
    except (NotFound, Forbidden, GoogleAPICallError) as e:
        logger.error("Dados do painel da gestora inacessíveis: %s", e)
        raise DadosIndisponiveisError("Os dados do painel estão indisponíveis.") from e
    return regras.PainelDaGestora(mercado, inadimplencia, rating, setores, blocos)
