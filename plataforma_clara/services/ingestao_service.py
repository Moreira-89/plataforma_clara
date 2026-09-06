"""
Serviço de ingestão de aportes a partir de um arquivo CSV.

Extraído de `IngestaoDadosState.lidar_com_upload_de_arquivo`, que misturava upload,
processamento, persistência e preparo do payload do BigQuery dentro de uma closure
de um event handler do Reflex. Agora o state só recebe o arquivo e chama isto.

É este o fluxo que a Fase 3 transforma: em vez de gravar no Postgres e depois
empurrar para o BigQuery na mão, a gravação emite um evento `AporteIngerido` na
mesma transação (outbox), e um consumidor idempotente cuida do BigQuery.
"""

import datetime
import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from sqlmodel import Session

from plataforma_clara.domain.schemas import ResultadoIngestao
from plataforma_clara.infra.db import sessao as sessao_padrao
from plataforma_clara.infra.repositorios.aporte import AporteRepositorio
from plataforma_clara.services.csv_processor import (
    COLUNAS_OBRIGATORIAS,
    processar_arquivo_csv,
)

logger = logging.getLogger(__name__)

FabricaDeSessao = Callable[[], AbstractContextManager[Session]]

# Colunas de data que o BigQuery recebe como string ISO 8601, não como objeto date.
_COLUNAS_DATA_BIGQUERY = ("data_vencimento", "data_referencia_competencia")


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


def ingerir_csv(
    caminho_arquivo: str | Any,
    *,
    sessao_factory: FabricaDeSessao = sessao_padrao,
) -> ResultadoIngestao:
    """
    Processa um CSV de aportes e persiste as linhas válidas no PostgreSQL.

    COMO FUNCIONA:
        1. Processamento — `processar_arquivo_csv` valida o schema das 19 colunas,
           coage os tipos e descarta as linhas inutilizáveis. Um arquivo fora do
           padrão levanta ValueError aqui.
        2. Montagem — Cada linha vira um registro com UUID novo, mais uma cópia
           com datas em ISO para o BigQuery.
        3. Persistência — Inserção em lote numa única transação.
        4. Retorno — Quantidade inserida e o payload do BigQuery, que o chamador
           envia em segundo plano.

    Todo o trabalho aqui é bloqueante (disco, pandas, banco): chame dentro de
    `asyncio.to_thread` a partir de código assíncrono.

    Args:
        caminho_arquivo (str | Path): Caminho do CSV já gravado em disco.
        sessao_factory (FabricaDeSessao): Fábrica de sessão de banco.

    Returns:
        ResultadoIngestao: Quantidade inserida e registros prontos para o BigQuery.

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

    # --- 3. PERSISTÊNCIA ---
    with sessao_factory() as sessao:
        quantidade = AporteRepositorio(sessao).inserir_em_lote(registros)

    # --- 4. RETORNO ---
    return ResultadoIngestao(
        quantidade_inserida=quantidade,
        registros_bigquery=registros_bigquery,
    )
