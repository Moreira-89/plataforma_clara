import logging
import os
import uuid
from typing import Any
import datetime

import pandas as pd
import reflex as rx
from google.cloud import bigquery

from plataforma_clara.model.schemas import tb_aporte
from plataforma_clara.services.csv_processor import processar_arquivo_csv

logger = logging.getLogger(__name__)

# Campos do modelo tb_aporte que devem ser enviados ao BigQuery (exclui 'id' do SQLModel)
_CAMPOS_APORTE: list[str] = [
    "id_aporte_uuid",
    "documento_investidor_cpf_cnpj",
    "fundo_origem_id",
    "nome_fundo_investidor",
    "empresa_sacada_nome",
    "cnpj_sacado_limpo",
    "valor_aporte_compra",
    "valor_mercado_atual",
    "quantidade_papeis_adquiridos",
    "data_vencimento",
    "data_referencia_competencia",
    "prazo_vencimento_dias",
    "status_prazo_vencimento",
    "taxa_retorno_pre_fixada",
    "bloco_liquidez_setorial",
    "categoria_tecnica_ativo",
    "codigo_identificacao_isin",
    "score_risco_interno",
    "flag_outlier_valor"
]


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
        caminho_temporario = None

        try:
            if not files:
                self.mensagem_para_usuario = "Nenhum arquivo foi enviado."
                return

            dados_arquivos = await files[0].read()
            caminho_temporario = rx.get_upload_dir() / files[0].filename

            with open(caminho_temporario, "wb") as f:
                f.write(dados_arquivos)



            dataframe = processar_arquivo_csv(caminho_temporario)

            # Converte DataFrame para lista de dicts de uma vez (evita iterrows lento)
            registros = dataframe.to_dict(orient="records")

            # Lista para guardar os dados enriquecidos com UUID para BigQuery
            dados_para_envio_bq: list[dict[str, Any]] = []

            with rx.session() as session:
                objetos_aporte: list[tb_aporte] = []

                for registro in registros:
                    novo_uuid = str(uuid.uuid4())

                    aporte = tb_aporte(
                        id_aporte_uuid=novo_uuid,
                        documento_investidor_cpf_cnpj=registro.get("documento_investidor_cpf_cnpj"),
                        fundo_origem_id=registro.get("fundo_origem_id"),
                        nome_fundo_investidor=registro.get("nome_fundo_investidor"),
                        empresa_sacada_nome=registro.get("empresa_sacada_nome"),
                        cnpj_sacado_limpo=registro.get("cnpj_sacado_limpo"),
                        valor_aporte_compra=registro.get("valor_aporte_compra"),
                        valor_mercado_atual=registro.get("valor_mercado_atual"),
                        quantidade_papeis_adquiridos=registro.get("quantidade_papeis_adquiridos"),
                        data_vencimento=registro.get("data_vencimento"),
                        data_referencia_competencia=registro.get("data_referencia_competencia"),
                        prazo_vencimento_dias=registro.get("prazo_vencimento_dias"),
                        status_prazo_vencimento=registro.get("status_prazo_vencimento"),
                        taxa_retorno_pre_fixada=registro.get("taxa_retorno_pre_fixada"),
                        bloco_liquidez_setorial=registro.get("bloco_liquidez_setorial"),
                        categoria_tecnica_ativo=registro.get("categoria_tecnica_ativo"),
                        codigo_identificacao_isin=registro.get("codigo_identificacao_isin"),
                        score_risco_interno=registro.get("score_risco_interno"),
                        flag_outlier_valor=registro.get("flag_outlier_valor"),
                    )
                    objetos_aporte.append(aporte)

                    # Monta dict para BigQuery usando a lista explícita de campos
                    d = {campo: getattr(aporte, campo) for campo in _CAMPOS_APORTE}
                    
                    if isinstance(d.get("data_vencimento"), datetime.date):
                        d["data_vencimento"] = d["data_vencimento"].isoformat()
                    if isinstance(d.get("data_referencia_competencia"), datetime.date):
                        d["data_referencia_competencia"] = d["data_referencia_competencia"].isoformat()
                        
                    dados_para_envio_bq.append(d)

                # Inserção em lote — mais eficiente que add() dentro do loop
                session.add_all(objetos_aporte)
                session.commit()

            logger.info(
                "%d aportes salvos no Supabase com sucesso.", len(objetos_aporte)
            )


            self.mensagem_para_usuario = (
                "Sucesso! CSV processado no Supabase e enviado para a nuvem."
            )

            # Chama a função em background para carregar no GCP
            yield IngestaoDadosState.enviar_dados_bigquery(dados_para_envio_bq)

        except ValueError as e:

            self.mensagem_para_usuario = str(e)
        except Exception as e:
            logger.exception("Erro inesperado no processamento do CSV.")

            self.mensagem_para_usuario = f"Erro no processamento: {str(e)}"
        finally:
            # Garante remoção do arquivo temporário mesmo em caso de exceção
            if caminho_temporario and os.path.exists(caminho_temporario):
                try:
                    os.remove(caminho_temporario)
                except OSError:
                    logger.warning(
                        "Não foi possível remover arquivo temporário: %s",
                        caminho_temporario,
                    )

    @rx.event(background=True)
    async def enviar_dados_bigquery(self, dados: list[dict]):
        """Envia dados processados para o BigQuery em background."""
        try:
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

            logger.info("Dados inseridos com sucesso na %s.", table_id)

        except Exception:
            logger.exception("Falha ao enviar para o BigQuery.")