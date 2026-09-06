"""
Estado de ingestão de arquivos CSV da Plataforma Clara.

Depois da extração do domínio, este state cuida do que é do Reflex: receber o
upload, gravar o arquivo temporário, exibir status e disparar a background task do
BigQuery. O processamento e a persistência estão em `services/ingestao_service.py`.

A dupla escrita continua como está: o Postgres é confirmado primeiro e o BigQuery
depois, fora de qualquer transação. É a D3 do roadmap, e é a Fase 3 que a fecha
com o padrão outbox.
"""

import asyncio
import logging
import os
from typing import Any

import pandas as pd
import reflex as rx
from google.cloud import bigquery

from plataforma_clara.services.bigquery_utils import criar_cliente_bigquery
from plataforma_clara.services.ingestao_service import ingerir_csv

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

_TABELA_BIGQUERY = "plataforma-clara.dados_fidc.tb_aporte"

# Schema explícito para o job de carga. Definido à mão para que o BigQuery não
# infira tipos errados a partir do DataFrame (ex: prazo em dias virar FLOAT).
# Precisa continuar espelhando as colunas de `domain/models.py::Aporte`.
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


# -----------------------------------------------------------------------------
# ESTADO DE INGESTÃO
# -----------------------------------------------------------------------------


class IngestaoDadosState(rx.State):
    """
    Estado responsável pelo fluxo de upload e processamento de CSVs.

    Comunica o andamento pela var `mensagem_para_usuario`. Todo o trabalho pesado
    roda em thread separada para não travar a UI.
    """

    mensagem_para_usuario: str = ""

    # -----------------------------------------------------------------------------
    # EVENTO PRINCIPAL DE UPLOAD
    # -----------------------------------------------------------------------------

    @rx.event
    async def lidar_com_upload_de_arquivo(self, files: list[rx.UploadFile]):
        """
        Recebe o CSV enviado, persiste no Supabase e dispara o envio ao BigQuery.

        COMO FUNCIONA:
            1. Validação do Arquivo — Presença, nome e extensão .csv.
            2. Leitura dos Bytes — O conteúdo é lido antes de qualquer gravação.
            3. Ingestão em Thread — Gravar o temporário, processar e inserir são
               operações bloqueantes; `asyncio.to_thread` mantém o event loop livre.
            4. Deleção do Temporário — Sempre, no `finally`.
            5. Envio ao BigQuery — Background task, para o usuário não esperar.

        Args:
            files (list[rx.UploadFile]): Arquivos do componente rx.upload. O nome
                                         do parâmetro DEVE ser ``files`` para casar
                                         com o contrato interno do Reflex.
        """
        self.mensagem_para_usuario = ""

        try:
            # --- 1. VALIDAÇÃO DO ARQUIVO ---
            if not files:
                self.mensagem_para_usuario = "Nenhum arquivo foi enviado."
                return

            # --- 2. LEITURA DOS BYTES ---
            conteudo = await files[0].read()
            nome_arquivo = os.path.basename(files[0].filename or "")

            if not nome_arquivo:
                self.mensagem_para_usuario = "Nome de arquivo inválido."
                return

            if not nome_arquivo.lower().endswith(".csv"):
                self.mensagem_para_usuario = "Formato inválido. Envie um arquivo .csv."
                return

            # --- 3. INGESTÃO EM THREAD ---
            resultado = await asyncio.to_thread(self._gravar_e_ingerir, nome_arquivo, conteudo)

            if resultado.quantidade_inserida == 0:
                self.mensagem_para_usuario = (
                    "Arquivo processado, mas sem linhas válidas para inserção."
                )
                return

            logger.info("%d aportes salvos no Supabase com sucesso.", resultado.quantidade_inserida)
            self.mensagem_para_usuario = (
                "Sucesso! CSV processado no Supabase e enviado para a nuvem."
            )

            # --- 5. ENVIO PARA BIGQUERY ---
            yield IngestaoDadosState.enviar_dados_bigquery(resultado.registros_bigquery)

        except ValueError as erro:
            # Erros de contrato do CSV chegam com mensagem pronta para a tela.
            self.mensagem_para_usuario = str(erro)
        except Exception as erro:
            logger.exception("Erro inesperado no processamento do CSV.")
            self.mensagem_para_usuario = f"Erro no processamento: {erro}"

    @staticmethod
    def _gravar_e_ingerir(nome_arquivo: str, conteudo: bytes):
        """
        Grava o CSV no diretório de upload, ingere e apaga o temporário.

        Executada em thread isolada. O arquivo é removido no `finally`, com ou sem
        sucesso — deixá-lo no disco acumularia CSVs com dados de investidores no
        diretório servido pelo Reflex.

        Args:
            nome_arquivo (str): Nome do arquivo enviado, já sanitizado por basename.
            conteudo (bytes): Conteúdo do CSV.

        Returns:
            ResultadoIngestao: Quantidade inserida e registros para o BigQuery.
        """
        caminho_temporario = rx.get_upload_dir() / nome_arquivo

        with open(caminho_temporario, "wb") as arquivo:
            arquivo.write(conteudo)

        try:
            return ingerir_csv(caminho_temporario)
        finally:
            # --- 4. DELEÇÃO DO TEMPORÁRIO ---
            if os.path.exists(caminho_temporario):
                try:
                    os.remove(caminho_temporario)
                except OSError:
                    logger.warning(
                        "Não foi possível remover arquivo temporário: %s", caminho_temporario
                    )

    # -----------------------------------------------------------------------------
    # BACKGROUND TASK — BIGQUERY
    # -----------------------------------------------------------------------------

    @rx.event(background=True)
    async def enviar_dados_bigquery(self, dados: list[dict[str, Any]]):
        """
        Envia os aportes já persistidos para o BigQuery, sem bloquear o event loop.

        COMO FUNCIONA:
            1. Tarefa em Thread — `load_table_from_dataframe` é síncrona e faz I/O
               de rede.
            2. Schema Explícito — Evita inferência de tipo errada pelo BigQuery.
            3. WRITE_APPEND — Acrescenta à tabela, nunca substitui.

        Uma falha aqui é apenas registrada: o usuário já recebeu a confirmação de
        sucesso, e os dados ficam divergentes entre Postgres e BigQuery em silêncio
        (D3 no roadmap).

        Args:
            dados (list[dict]): Aportes convertidos para o formato do BigQuery.
        """

        def _carregar():
            """Executado em thread separada — operação síncrona de I/O de rede."""
            cliente = criar_cliente_bigquery(project_id="plataforma-clara")
            configuracao = bigquery.LoadJobConfig(
                schema=_SCHEMA_BIGQUERY,
                write_disposition="WRITE_APPEND",
            )
            job = cliente.load_table_from_dataframe(
                pd.DataFrame(dados), _TABELA_BIGQUERY, job_config=configuracao
            )
            job.result()  # Aguarda a conclusão do job de carga

        try:
            await asyncio.to_thread(_carregar)
            logger.info("Dados inseridos com sucesso no BigQuery.")
        except Exception:
            logger.exception("Falha ao enviar para o BigQuery.")
