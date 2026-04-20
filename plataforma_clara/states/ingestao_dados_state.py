import logging
import os
import uuid
from typing import Any
import datetime
import asyncio

import pandas as pd
import reflex as rx
from google.cloud import bigquery

from plataforma_clara.model.schemas import tb_aporte
from plataforma_clara.services.csv_processor import processar_arquivo_csv

logger = logging.getLogger(__name__)


class IngestaoDadosState(rx.State):
    """Estado responsável pelo fluxo de upload e processamento de CSVs."""

    mensagem_para_usuario: str = ""


    @rx.event
    async def lidar_com_upload_de_arquivo(self, files: list[rx.UploadFile]):
        """
        Recebe arquivo CSV via upload, processa e persiste no Supabase + BigQuery.

        O Reflex envia os arquivos selecionados como keyword argument ``files``.
        O parâmetro DEVE se chamar ``files`` para casar com o contrato do framework.
        """
        self.mensagem_para_usuario = ""

        try:
            if not files:
                self.mensagem_para_usuario = "Nenhum arquivo foi enviado."
                return

            dados_arquivos = await files[0].read()
            filename = os.path.basename(files[0].filename or "")

            if not filename:
                self.mensagem_para_usuario = "Nome de arquivo inválido."
                return

            if not filename.lower().endswith(".csv"):
                self.mensagem_para_usuario = "Formato inválido. Envie um arquivo .csv."
                return

            def _processar_arquivo():
                caminho_temporario = rx.get_upload_dir() / filename
                
                with open(caminho_temporario, "wb") as f:
                    f.write(dados_arquivos)

                try:
                    dataframe = processar_arquivo_csv(caminho_temporario)
                    registros = dataframe.to_dict(orient="records")

                    dados_db = []
                    dados_para_envio_bq = []

                    for registro in registros:
                        novo_uuid = str(uuid.uuid4())
                        
                        d = {
                            "id_aporte_uuid": novo_uuid,
                            "documento_investidor_cpf_cnpj": registro.get("documento_investidor_cpf_cnpj"),
                            "fundo_origem_id": registro.get("fundo_origem_id"),
                            "nome_fundo_investidor": registro.get("nome_fundo_investidor"),
                            "empresa_sacada_nome": registro.get("empresa_sacada_nome"),
                            "cnpj_sacado_limpo": registro.get("cnpj_sacado_limpo"),
                            "valor_aporte_compra": registro.get("valor_aporte_compra"),
                            "valor_mercado_atual": registro.get("valor_mercado_atual"),
                            "quantidade_papeis_adquiridos": registro.get("quantidade_papeis_adquiridos"),
                            "data_vencimento": registro.get("data_vencimento"),
                            "data_referencia_competencia": registro.get("data_referencia_competencia"),
                            "prazo_vencimento_dias": registro.get("prazo_vencimento_dias"),
                            "status_prazo_vencimento": registro.get("status_prazo_vencimento"),
                            "taxa_retorno_pre_fixada": registro.get("taxa_retorno_pre_fixada"),
                            "bloco_liquidez_setorial": registro.get("bloco_liquidez_setorial"),
                            "categoria_tecnica_ativo": registro.get("categoria_tecnica_ativo"),
                            "codigo_identificacao_isin": registro.get("codigo_identificacao_isin"),
                            "score_risco_interno": registro.get("score_risco_interno"),
                            "flag_outlier_valor": registro.get("flag_outlier_valor"),
                        }
                        dados_db.append(d)

                        # Preparação para o BQ
                        bq_dict = dict(d)
                        if isinstance(bq_dict.get("data_vencimento"), datetime.date):
                            bq_dict["data_vencimento"] = bq_dict["data_vencimento"].isoformat()
                        if isinstance(bq_dict.get("data_referencia_competencia"), datetime.date):
                            bq_dict["data_referencia_competencia"] = bq_dict["data_referencia_competencia"].isoformat()
                            
                        dados_para_envio_bq.append(bq_dict)

                    with rx.session() as session:
                        session.bulk_insert_mappings(tb_aporte, dados_db)
                        session.commit()

                    return len(dados_db), dados_para_envio_bq

                finally:
                    if os.path.exists(caminho_temporario):
                        try:
                            os.remove(caminho_temporario)
                        except OSError:
                            logger.warning("Não foi possível remover arquivo temporário: %s", caminho_temporario)

            # Executa toda a leitura do pandas e DB insert em thread isolada
            qtd_inseridos, bq_dados = await asyncio.to_thread(_processar_arquivo)

            if qtd_inseridos == 0:
                self.mensagem_para_usuario = (
                    "Arquivo processado, mas sem linhas válidas para inserção."
                )
                return

            logger.info("%d aportes salvos no Supabase com sucesso.", qtd_inseridos)

            self.mensagem_para_usuario = "Sucesso! CSV processado no Supabase e enviado para a nuvem."

            # Chama a função em background para carregar no GCP
            yield IngestaoDadosState.enviar_dados_bigquery(bq_dados)

        except ValueError as e:
            self.mensagem_para_usuario = str(e)
        except Exception as e:
            logger.exception("Erro inesperado no processamento do CSV.")
            self.mensagem_para_usuario = f"Erro no processamento: {str(e)}"

    @rx.event(background=True)
    async def enviar_dados_bigquery(self, dados: list[dict[str, Any]]):
        """Envia dados processados para o BigQuery em background sem bloquear o event loop."""
        def _bq_task():
            client = bigquery.Client()
            table_id = "plataforma-clara.dados_fidc.tb_aporte"

            dataframe_bigquery = pd.DataFrame(dados)

            job_config = bigquery.LoadJobConfig(
                schema=[
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
                ],
                write_disposition="WRITE_APPEND",
            )

            job = client.load_table_from_dataframe(
                dataframe_bigquery, table_id, job_config=job_config
            )
            job.result()
            
        try:
            await asyncio.to_thread(_bq_task)
            logger.info("Dados inseridos com sucesso no BigQuery.")
        except Exception:
            logger.exception("Falha ao enviar para o BigQuery.")
