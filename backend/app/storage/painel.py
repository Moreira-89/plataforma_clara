"""
Leitura dos dados do painel da gestora no BigQuery (dataset `BIGQUERY_DATASET_EMPRESAS`).

COMO FUNCIONA:
    1. Consulta as views do mercado de FIDCs (resumo, série mensal, rating e setores), a dos blocos
       e as tabelas de score e de empresas (distribuição dos scores e alertas dos blocos).
    2. As consultas rodam em paralelo; rating e setores pegam só o mês mais recente.
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


def _serie_mercado() -> list[regras.PontoMercado]:
    sql = f"""
        SELECT DT_COMPETENCIA, TX_INADIMPLENCIA, VL_PL_TOTAL, QTD_FUNDOS_ATIVOS
        FROM {tabela("vw_cvm_mercado_mensal", _DATASET)}
        ORDER BY DT_COMPETENCIA
    """
    return [
        regras.PontoMercado(
            r.DT_COMPETENCIA,
            regras.para_percentual(r.TX_INADIMPLENCIA),
            float(r.VL_PL_TOTAL),
            r.QTD_FUNDOS_ATIVOS,
        )
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
        SELECT SETOR, GRUPO, PCT_MERCADO, PCT_NO_GRUPO, TX_INAD_AGREGADA_CONCENTRADOS
        FROM {view}
        WHERE DT_COMPETENCIA = (SELECT MAX(DT_COMPETENCIA) FROM {view})
        ORDER BY PCT_MERCADO DESC
    """
    return [
        regras.SetorBenchmark(
            r.SETOR,
            r.GRUPO,
            regras.para_percentual(r.PCT_MERCADO),
            regras.para_percentual(r.PCT_NO_GRUPO),
            regras.para_percentual(r.TX_INAD_AGREGADA_CONCENTRADOS),
        )
        for r in _linhas(sql)
    ]


def _blocos() -> list[regras.BlocoDoPainel]:
    pt = "SAFE_DIVIDE(SUM({c} * capital_estimado), SUM(capital_estimado))"
    sql = f"""
        SELECT b.id_bloco, b.codigo_identificacao, b.etiqueta, b.capital_total, b.QTD_EMPRESAS,
               b.SCORE_BLOCO, b.NOTA_BLOCO, b.SETORES_CVM,
               c.qualidade, c.permanencia, c.risco_setor, c.aceitacao
        FROM {tabela("vw_blocos_score", _DATASET)} b
        LEFT JOIN (
            SELECT id_bloco,
                   {pt.format(c="PT_QUALIDADE_FUNDOS")} AS qualidade,
                   {pt.format(c="PT_PERMANENCIA")} AS permanencia,
                   {pt.format(c="PT_RISCO_SETOR")} AS risco_setor,
                   {pt.format(c="PT_ACEITACAO")} AS aceitacao
            FROM {tabela("vw_blocos_empresas_score", _DATASET)}
            GROUP BY id_bloco
        ) c ON c.id_bloco = b.id_bloco
        ORDER BY b.SCORE_BLOCO DESC
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
            componentes=None
            if r.qualidade is None
            else regras.ComponentesScore(
                float(r.qualidade), float(r.permanencia), float(r.risco_setor), float(r.aceitacao)
            ),
        )
        for r in _linhas(sql)
    ]


def _capital_por_setor() -> dict[str, float]:
    sql = f"""
        SELECT SETOR_CVM, SUM(capital_estimado) AS capital
        FROM {tabela("vw_blocos_empresas_score", _DATASET)}
        WHERE SETOR_CVM IS NOT NULL
        GROUP BY SETOR_CVM
    """
    return {r.SETOR_CVM: float(r.capital) for r in _linhas(sql)}


def _distribuicao_scores() -> list[regras.FaixaDeScore]:
    sql = f"""
        SELECT CAST(FLOOR(SCORE / 10) * 10 AS INT64) AS inicio, COUNT(*) AS empresas,
               COUNTIF(PERFIL_COMPARTILHADO) AS compartilhado
        FROM {tabela("tb_score_empresas", _DATASET)}
        GROUP BY inicio
        ORDER BY inicio
    """
    return [regras.FaixaDeScore(r.inicio, r.empresas, r.compartilhado) for r in _linhas(sql)]


def _alertas() -> list[regras.EmpresaComAlerta]:
    sql = f"""
        SELECT s.ID_EMPRESA, COALESCE(e.NOME_FANTASIA, e.RAZAO_SOCIAL, e.CNPJ) AS nome,
               b.etiqueta, s.SCORE, s.ALERTAS
        FROM {tabela("tb_score_empresas", _DATASET)} s
        JOIN {tabela("vw_blocos_empresas_score", _DATASET)} be ON be.id_empresa = s.ID_EMPRESA
        JOIN {tabela("vw_blocos_score", _DATASET)} b ON b.id_bloco = be.id_bloco
        LEFT JOIN {tabela("tb_empresas_fidc", _DATASET)} e ON CAST(e.ID_EMPRESA AS STRING) = s.ID_EMPRESA
        WHERE s.ALERTAS IS NOT NULL AND s.ALERTAS != ''
        ORDER BY s.SCORE, nome
    """
    return [
        regras.EmpresaComAlerta(r.ID_EMPRESA, r.nome or r.ID_EMPRESA, r.etiqueta, float(r.SCORE), r.ALERTAS)
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
        consultas = (
            _mercado, _serie_mercado, _rating, _setores, _blocos,
            _capital_por_setor, _distribuicao_scores, _alertas,
        )  # fmt: skip
        with ThreadPoolExecutor(max_workers=len(consultas)) as pool:
            tarefas = [pool.submit(f) for f in consultas]
            mercado, serie, rating, setores, blocos, capital_setor, distribuicao, alertas = (
                t.result() for t in tarefas
            )
    except (NotFound, Forbidden, GoogleAPICallError) as e:
        logger.error("Dados do painel da gestora inacessíveis: %s", e)
        raise DadosIndisponiveisError("Os dados do painel estão indisponíveis.") from e
    exposicao = regras.montar_exposicao(capital_setor, setores)
    return regras.PainelDaGestora(
        mercado, serie, rating, setores, blocos, exposicao, distribuicao, alertas
    )
