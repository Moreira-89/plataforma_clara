"""
Busca de empresas no cadastro (`tb_empresas_fidc`, no BigQuery).

COMO FUNCIONA:
    1. Procura pelo texto no nome fantasia ou, se houver dígitos, no CNPJ, em
       `tb_empresas_fidc` (dataset `BIGQUERY_DATASET_EMPRESAS`).
    2. Deixa de fora as empresas que já pertencem a algum bloco.
    3. A consulta é parametrizada; o texto do usuário nunca entra no SQL.

Args:
    Nenhum.

Returns:
    list[EmpresaCatalogo]: via `buscar_empresas()`.

Raises:
    DadosIndisponiveisError: Tabela de empresas ou de blocos fora do ar.
"""

import logging

from google.api_core.exceptions import Forbidden, NotFound
from google.cloud import bigquery

from app.config.settings import settings
from app.domain.blocos import EmpresaCatalogo
from app.domain.erros import DadosIndisponiveisError
from app.domain.identidade import normalizar_documento
from app.storage.bigquery import cliente_compartilhado, tabela

logger = logging.getLogger(__name__)

TABELA_EMPRESAS = "tb_empresas_fidc"
TABELA_BLOCOS_EMPRESAS = "tb_blocos_empresas"

_CNPJ_LIMPO = r"REGEXP_REPLACE(CAST(e.CNPJ AS STRING), r'\D', '')"


def tabela_empresas() -> str:
    """Tabela do cadastro de empresas, que mora em outro dataset que a dos blocos."""
    return tabela(TABELA_EMPRESAS, settings.bigquery_dataset_empresas)


def buscar_empresas(busca: str, limite: int = 20) -> list[EmpresaCatalogo]:
    """
    Busca empresas livres (fora de qualquer bloco) por nome fantasia ou CNPJ. Bloqueante.

    Args:
        busca (str): Texto digitado, com ou sem máscara de CNPJ.
        limite (int): Máximo de resultados.

    Returns:
        list[EmpresaCatalogo]: Empresas encontradas, em ordem alfabética.

    Raises:
        DadosIndisponiveisError: Tabela de empresas ou de blocos fora do ar.
    """
    sql = f"""
        SELECT CAST(e.ID_EMPRESA AS STRING) AS id_empresa,
               COALESCE(e.NOME_FANTASIA, e.RAZAO_SOCIAL, '') AS nome_fantasia,
               COALESCE(e.RAZAO_SOCIAL, '') AS razao_social,
               {_CNPJ_LIMPO} AS cnpj,
               COALESCE(e.RAMO_EMPRESA, '') AS ramo_atividade
        FROM {tabela_empresas()} e
        WHERE e.ID_EMPRESA IS NOT NULL AND e.CNPJ IS NOT NULL
          AND (STRPOS(LOWER(COALESCE(e.NOME_FANTASIA, e.RAZAO_SOCIAL, '')), LOWER(@texto)) > 0
               OR (@digitos != '' AND STRPOS({_CNPJ_LIMPO}, @digitos) > 0))
          AND CAST(e.ID_EMPRESA AS STRING) NOT IN (
              SELECT b.id_empresa FROM {tabela(TABELA_BLOCOS_EMPRESAS)} b)
        ORDER BY nome_fantasia
        LIMIT @limite
    """
    config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("texto", "STRING", busca.strip()),
            bigquery.ScalarQueryParameter("digitos", "STRING", normalizar_documento(busca)),
            bigquery.ScalarQueryParameter("limite", "INT64", limite),
        ]
    )
    try:
        linhas = cliente_compartilhado().query(sql, job_config=config).result()
        return [
            EmpresaCatalogo(
                id_empresa=r.id_empresa,
                nome_fantasia=r.nome_fantasia,
                razao_social=r.razao_social,
                cnpj=r.cnpj,
                ramo_atividade=r.ramo_atividade,
            )
            for r in linhas
        ]
    except (NotFound, Forbidden) as e:
        logger.error("Cadastro de empresas inacessível: %s", e)
        raise DadosIndisponiveisError("O cadastro de empresas está indisponível.") from e
