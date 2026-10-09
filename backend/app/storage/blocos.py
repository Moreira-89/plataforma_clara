"""
Gravação dos Blocos de Liquidez no BigQuery (`tb_blocos_liquidez` e `tb_blocos_empresas`).

COMO FUNCIONA:
    1. Confere que todas as empresas existem em `tb_empresas`.
    2. Confere que nenhuma já pertence a outro bloco.
    3. Grava o bloco e as suas empresas numa única transação, para não sobrar bloco
       pela metade se algo falhar.
    4. `criar_tabelas` cria as duas tabelas, sem apagar nada se já existirem.

Args:
    Nenhum.

Returns:
    None: via `criar_bloco()`.

Raises:
    EmpresaNaoEncontradaError: Empresa fora do cadastro.
    EmpresaJaEmBlocoError: Empresa já alocada a outro bloco.
    DadosIndisponiveisError: Alguma tabela fora do ar.
"""

import logging

from google.api_core.exceptions import Forbidden, NotFound
from google.cloud import bigquery

from app.domain.blocos import BlocoValidado
from app.domain.erros import (
    DadosIndisponiveisError,
    EmpresaJaEmBlocoError,
    EmpresaNaoEncontradaError,
)
from app.storage.bigquery import cliente_compartilhado, tabela
from app.storage.empresas import TABELA_BLOCOS_EMPRESAS, TABELA_EMPRESAS

logger = logging.getLogger(__name__)

TABELA_BLOCOS = "tb_blocos_liquidez"


def criar_tabelas() -> None:
    """Cria `tb_blocos_liquidez` e `tb_blocos_empresas` se ainda não existirem."""
    cliente = cliente_compartilhado()
    cliente.query(
        f"""
        CREATE TABLE IF NOT EXISTS {tabela(TABELA_BLOCOS)} (
            id_bloco STRING NOT NULL,
            codigo_identificacao STRING NOT NULL,
            etiqueta STRING NOT NULL,
            capital_total NUMERIC NOT NULL,
            data_criacao DATE NOT NULL,
            data_vencimento DATE NOT NULL,
            responsavel_tecnico STRING NOT NULL,
            observacao STRING,
            criado_por_uid STRING NOT NULL,
            criado_em TIMESTAMP NOT NULL
        )
        """
    ).result()
    cliente.query(
        f"""
        CREATE TABLE IF NOT EXISTS {tabela(TABELA_BLOCOS_EMPRESAS)} (
            id_bloco STRING NOT NULL,
            id_empresa STRING NOT NULL,
            cnpj STRING NOT NULL,
            capital_estimado NUMERIC NOT NULL,
            percentual_liquidez NUMERIC NOT NULL
        )
        """
    ).result()


def _ids_param(ids: list[str]) -> bigquery.QueryJobConfig:
    return bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("ids", "STRING", ids)]
    )


def _cnpjs_do_cadastro(cliente: bigquery.Client, ids: list[str]) -> dict[str, str]:
    sql = f"""
        SELECT CAST(id_empresa AS STRING) AS id_empresa,
               REGEXP_REPLACE(CAST(cnpj AS STRING), r'\\D', '') AS cnpj
        FROM {tabela(TABELA_EMPRESAS)}
        WHERE CAST(id_empresa AS STRING) IN UNNEST(@ids)
    """
    return {r.id_empresa: r.cnpj for r in cliente.query(sql, job_config=_ids_param(ids)).result()}


def _ja_em_bloco(cliente: bigquery.Client, ids: list[str]) -> set[str]:
    sql = (
        f"SELECT id_empresa FROM {tabela(TABELA_BLOCOS_EMPRESAS)} WHERE id_empresa IN UNNEST(@ids)"
    )
    return {r.id_empresa for r in cliente.query(sql, job_config=_ids_param(ids)).result()}


def criar_bloco(bloco: BlocoValidado, uid: str) -> None:
    """
    Grava o bloco e as suas empresas. Bloqueante.

    Args:
        bloco (BlocoValidado): Bloco já validado pelo domínio.
        uid (str): Uid da gestora que criou o bloco.

    Raises:
        EmpresaNaoEncontradaError: Empresa fora do cadastro.
        EmpresaJaEmBlocoError: Empresa já alocada a outro bloco.
        DadosIndisponiveisError: Alguma tabela fora do ar.
    """
    cliente = cliente_compartilhado()
    ids = [e.id_empresa for e in bloco.empresas]
    try:
        cnpjs = _cnpjs_do_cadastro(cliente, ids)
        if faltando := sorted(set(ids) - set(cnpjs)):
            raise EmpresaNaoEncontradaError(f"Empresa fora do cadastro: {', '.join(faltando)}.")
        if ocupadas := sorted(_ja_em_bloco(cliente, ids)):
            raise EmpresaJaEmBlocoError(
                f"Empresa já pertence a outro bloco: {', '.join(ocupadas)}."
            )
        _gravar(cliente, bloco, uid, cnpjs)
    except (NotFound, Forbidden) as e:
        logger.error("Tabela de blocos ou de empresas inacessível: %s", e)
        raise DadosIndisponiveisError("Os dados de blocos estão indisponíveis.") from e


def _gravar(
    cliente: bigquery.Client, bloco: BlocoValidado, uid: str, cnpjs: dict[str, str]
) -> None:
    script = f"""
        BEGIN TRANSACTION;
        INSERT INTO {tabela(TABELA_BLOCOS)}
            (id_bloco, codigo_identificacao, etiqueta, capital_total, data_criacao,
             data_vencimento, responsavel_tecnico, observacao, criado_por_uid, criado_em)
        VALUES (@id_bloco, @codigo, @etiqueta, @capital_total, @data_criacao,
                @data_vencimento, @responsavel, NULLIF(@observacao, ''), @uid, @criado_em);
        INSERT INTO {tabela(TABELA_BLOCOS_EMPRESAS)}
            (id_bloco, id_empresa, cnpj, capital_estimado, percentual_liquidez)
        SELECT @id_bloco, e.id_empresa, e.cnpj, e.capital_estimado, e.percentual_liquidez
        FROM UNNEST(@empresas) e;
        COMMIT TRANSACTION;
    """
    escalar = bigquery.ScalarQueryParameter
    empresas = [
        bigquery.StructQueryParameter(
            "",
            escalar("id_empresa", "STRING", e.id_empresa),
            escalar("cnpj", "STRING", cnpjs[e.id_empresa]),
            escalar("capital_estimado", "NUMERIC", e.capital_estimado),
            escalar("percentual_liquidez", "NUMERIC", e.percentual),
        )
        for e in bloco.empresas
    ]
    config = bigquery.QueryJobConfig(
        query_parameters=[
            escalar("id_bloco", "STRING", bloco.id_bloco),
            escalar("codigo", "STRING", bloco.codigo_identificacao),
            escalar("etiqueta", "STRING", bloco.etiqueta),
            escalar("capital_total", "NUMERIC", bloco.capital_total),
            escalar("data_criacao", "DATE", bloco.data_criacao),
            escalar("data_vencimento", "DATE", bloco.data_vencimento),
            escalar("responsavel", "STRING", bloco.responsavel_tecnico),
            escalar("observacao", "STRING", bloco.observacao),
            escalar("uid", "STRING", uid),
            escalar("criado_em", "TIMESTAMP", bloco.criado_em),
            bigquery.ArrayQueryParameter("empresas", "STRUCT", empresas),
        ]
    )
    cliente.query(script, job_config=config).result()
