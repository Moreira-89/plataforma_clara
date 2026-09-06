"""
Serviço de ingestão de aportes a partir de um arquivo CSV.

Processa o CSV de aportes e carrega os registros no BigQuery. Nada aqui depende de
camada de entrega — quem receber o upload só precisa entregar o caminho do arquivo.

PENDENTE: a gravação operacional. Com a saída do Postgres, a persistência de
consulta rápida passa a ser o Firestore, que ainda não está implementado. Hoje o
fluxo processa e envia ao BigQuery; falta o passo que grava o documento do aporte
no Firestore para o dashboard ler sem varrer o analítico.
"""

import datetime
import logging
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from google.cloud import bigquery

from app.api.schemas.contratos import ResultadoIngestao
from app.config.settings import settings
from app.ingestion.csv_processor import COLUNAS_OBRIGATORIAS, processar_arquivo_csv
from app.storage.bigquery import criar_cliente_bigquery

logger = logging.getLogger(__name__)

# Datas que o BigQuery recebe como string ISO 8601.
_COLUNAS_DATA_BIGQUERY = ("data_vencimento", "data_referencia_competencia")

_PROJETO_BIGQUERY = settings.project_id
_TABELA_BIGQUERY = f"{settings.project_id}.{settings.bigquery_dataset}.tb_aporte"

# Schema explícito do job: sem ele o BigQuery infere tipo errado do DataFrame.
_SCHEMA_BIGQUERY = [
    bigquery.SchemaField("id_aporte_uuid", "STRING"),
    bigquery.SchemaField("documento_investidor_cpf_cnpj", "STRING"),
    bigquery.SchemaField("fundo_origem_id", "STRING"),
    bigquery.SchemaField("nome_fundo_investidor", "STRING"),
    bigquery.SchemaField("empresa_sacada_nome", "STRING"),
    bigquery.SchemaField("cnpj_sacado_limpo", "STRING"),
    bigquery.SchemaField("valor_aporte_compra", "FLOAT"),
    bigquery.SchemaField("valor_mercado_atual", "FLOAT"),
    bigquery.SchemaField("quantidade_papeis_adquiridos", "FLOAT"),
    bigquery.SchemaField("data_vencimento", "STRING"),
    bigquery.SchemaField("data_referencia_competencia", "STRING"),
    bigquery.SchemaField("prazo_vencimento_dias", "INTEGER"),
    bigquery.SchemaField("status_prazo_vencimento", "STRING"),
    bigquery.SchemaField("taxa_retorno_pre_fixada", "FLOAT"),
    bigquery.SchemaField("bloco_liquidez_setorial", "STRING"),
    bigquery.SchemaField("categoria_tecnica_ativo", "STRING"),
    bigquery.SchemaField("codigo_identificacao_isin", "STRING"),
    bigquery.SchemaField("score_risco_interno", "FLOAT"),
    bigquery.SchemaField("flag_outlier_valor", "STRING"),
]


def _preparar_registro(linha: dict[str, Any]) -> dict[str, Any]:
    """
    Monta o registro de um aporte a partir de uma linha já processada do CSV.

    O `id_aporte_uuid` é SEMPRE gerado aqui, nunca reaproveitado do arquivo: reenviar
    o mesmo CSV precisa produzir registros novos, não colidir com os antigos. O preço
    é que a plataforma não tem como detectar um reenvio acidental — o que vira
    problema de verdade na Fase 3, onde o consumidor idempotente do BigQuery
    justamente usa esse UUID como chave de deduplicação.

    Args:
        linha (dict): Uma linha do DataFrame devolvido por `processar_arquivo_csv`.

    Returns:
        dict: Registro com as colunas de `tb_aporte` e um UUID novo.
    """
    registro = {coluna: linha.get(coluna) for coluna in COLUNAS_OBRIGATORIAS}
    registro["id_aporte_uuid"] = str(uuid.uuid4())
    return registro


def _para_bigquery(registro: dict[str, Any]) -> dict[str, Any]:
    """
    Converte um registro para o formato aceito pelo schema do BigQuery.

    Args:
        registro (dict): Registro pronto para o PostgreSQL.

    Returns:
        dict: Cópia com as datas convertidas para string ISO 8601.
    """
    convertido = dict(registro)
    for coluna in _COLUNAS_DATA_BIGQUERY:
        valor = convertido.get(coluna)
        if isinstance(valor, datetime.date):
            convertido[coluna] = valor.isoformat()
    return convertido


def ingerir_csv(caminho_arquivo: str | Path) -> ResultadoIngestao:
    """
    Processa um CSV de aportes e devolve os registros prontos para persistir.

    COMO FUNCIONA:
        1. Processamento — `processar_arquivo_csv` valida o schema das 19 colunas,
           coage os tipos e descarta as linhas inutilizáveis. Um arquivo fora do
           padrão levanta ValueError aqui.
        2. Montagem — Cada linha vira um registro com UUID novo, mais uma cópia
           com datas em ISO para o BigQuery.

    Todo o trabalho aqui é bloqueante (disco, pandas): chame dentro de
    `asyncio.to_thread` a partir de código assíncrono.

    Args:
        caminho_arquivo (str | Path): Caminho do CSV já gravado em disco.

    Returns:
        ResultadoIngestao: Quantidade processada e os registros nos dois formatos.

    Raises:
        ValueError: Se o arquivo não for um CSV válido ou faltar coluna obrigatória.
    """
    # --- 1. PROCESSAMENTO ---
    dataframe = processar_arquivo_csv(caminho_arquivo)

    # --- 2. MONTAGEM ---
    registros = [_preparar_registro(linha) for linha in dataframe.to_dict(orient="records")]
    if not registros:
        logger.info("CSV processado sem nenhuma linha válida para inserção.")
        return ResultadoIngestao(quantidade_inserida=0)

    registros_bigquery = [_para_bigquery(registro) for registro in registros]

    return ResultadoIngestao(
        quantidade_inserida=len(registros),
        registros=registros,
        registros_bigquery=registros_bigquery,
    )


def enviar_ao_bigquery(registros: list[dict[str, Any]]) -> int:
    """
    Carrega no BigQuery os aportes processados a partir do CSV.

    O schema da tabela analítica mora aqui: é o par do modelo em `domain/models.py`,
    e os dois precisam ser alterados juntos.

    COMO FUNCIONA:
        1. Monta o DataFrame a partir dos registros já convertidos por `_para_bigquery`.
        2. Configura o job com o schema explícito e `WRITE_APPEND` — acrescenta à
           tabela, nunca substitui.
        3. Aguarda a conclusão do job.

    É I/O de rede bloqueante: chame dentro de `asyncio.to_thread` a partir de
    código assíncrono.

    A exceção SOBE em vez de virar log: quem chama é que sabe se ainda dá tempo de
    avisar o usuário.

    Args:
        registros (list[dict]): Aportes no formato do BigQuery, com datas em ISO.

    Returns:
        int: Quantidade de registros enviados.

    Raises:
        Exception: Qualquer falha de credencial, schema ou rede do BigQuery.
    """
    if not registros:
        return 0

    cliente = criar_cliente_bigquery(project_id=_PROJETO_BIGQUERY)
    configuracao = bigquery.LoadJobConfig(
        schema=_SCHEMA_BIGQUERY,
        write_disposition="WRITE_APPEND",
    )

    job = cliente.load_table_from_dataframe(
        pd.DataFrame(registros), _TABELA_BIGQUERY, job_config=configuracao
    )
    job.result()  # Aguarda a conclusão do job de carga.

    logger.info("%d aportes enviados ao BigQuery.", len(registros))
    return len(registros)
