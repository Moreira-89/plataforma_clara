import os
import uuid # Biblioteca nativa para gerar IDs únicos
import pandas as pd
import reflex as rx
from google.cloud import bigquery
from dotenv import load_dotenv

from plataforma_clara.model.schemas import tb_aporte
from plataforma_clara.services.csv_processor import processar_arquivo_csv

class IngestaoDadosState(rx.State):
    load_dotenv()

    mensagem_para_usuario: str = ""
    processamento_ativo: bool = False

    async def lidar_com_upload_de_arquivo(self, arquivos: list[rx.UploadFile]):
        self.mensagem_para_usuario = ""
        caminho_temporario = None

        try:
            if not arquivos:
                self.mensagem_para_usuario = "Nenhum arquivo foi enviado."
                return

            dados_arquivos = await arquivos[0].read()
            caminho_temporario = rx.get_upload_dir() / arquivos[0].filename

            with open(caminho_temporario, "wb") as f:
                f.write(dados_arquivos)

            self.processamento_ativo = True
            yield

            dataframe = processar_arquivo_csv(caminho_temporario)

            # Lista para guardar os dados e enviar ao BigQuery com o mesmo UUID
            dados_para_envio_bq = []

            with rx.session() as session:
                for _, dados_da_linha in dataframe.iterrows():
                    # 1. Plataforma gera o UUID universal para este aporte
                    novo_uuid = str(uuid.uuid4())
                    
                    aporte = tb_aporte(
                        id_aporte_uuid=novo_uuid,
                        # Utilize .get() com fallback None caso a coluna falte no CSV para evitar quebras
                        fundo_origem_id=dados_da_linha.get("fundo_origem_id"),
                        nome_fundo_investidor=dados_da_linha.get("nome_fundo_investidor"),
                        empresa_sacada_nome=dados_da_linha.get("empresa_sacada_nome"),
                        cnpj_sacado_limpo=dados_da_linha.get("cnpj_sacado_limpo"),
                        valor_aporte_compra=dados_da_linha.get("valor_aporte_compra"),
                        valor_mercado_atual=dados_da_linha.get("valor_mercado_atual"),
                        taxa_retorno_pre_fixada=dados_da_linha.get("taxa_retorno_pre_fixada"),
                        prazo_vencimento_dias=dados_da_linha.get("prazo_vencimento_dias"),
                        quantidade_papeis_adquiridos=dados_da_linha.get("quantidade_papeis_adquiridos"),
                        score_risco_interno=dados_da_linha.get("score_risco_interno"),
                        status_prazo_vencimento=dados_da_linha.get("status_prazo_vencimento"),
                        bloco_liquidez_setorial=dados_da_linha.get("bloco_liquidez_setorial"),
                        categoria_tecnica_ativo=dados_da_linha.get("categoria_tecnica_ativo"),
                        codigo_identificacao_isin=dados_da_linha.get("codigo_identificacao_isin"),
                        codigo_identificacao_selic=dados_da_linha.get("codigo_identificacao_selic"),
                        # Certifique-se de que o CSV retorna uma data válida aqui:
                        data_referencia_competencia=dados_da_linha.get("data_referencia_competencia") 
                    )
                    session.add(aporte)
                    
                    # 2. Adiciona os dados enriquecidos com o UUID à lista do BigQuery
                    # Converter o modelo Pydantic/SQLModel de volta para dicionário para facilitar
                    dados_para_envio_bq.append(
                        {k: getattr(aporte, k) for k in aporte.__fields__.keys() if k != 'id'}
                    )

                session.commit()

            if caminho_temporario and os.path.exists(caminho_temporario):
                os.remove(caminho_temporario)

            self.processamento_ativo = False
            self.mensagem_para_usuario = "Sucesso! CSV processado no Supabase e enviado para a nuvem."

            # Chama a função em background para carregar no GCP
            yield IngestaoDadosState.enviar_dados_bigquery(dados_para_envio_bq)

        except ValueError as e:
            self.processamento_ativo = False
            self.mensagem_para_usuario = str(e)
        except Exception as e:
            self.processamento_ativo = False
            self.mensagem_para_usuario = f"Erro no processamento: {str(e)}"


    @rx.event(background=True)
    async def enviar_dados_bigquery(self, dados: list[dict]):
        try:
            # Puxa credenciais usando o ambiente (garanta que GOOGLE_APPLICATION_CREDENTIALS está no .env)
            client = bigquery.Client()
            
            # ATENÇÃO: Substitua pelo nome real do seu dataset e tabela criados no GCP
            table_id = "plataforma-clara.dados_fidc.tb_aporte"

            # Transforma a lista de dicionários num DataFrame
            dataframe_bigquery = pd.DataFrame(dados)

            # Define estritamente o Schema espelhando o schemas.py
            job_config = bigquery.LoadJobConfig(
                schema=[
                    bigquery.SchemaField("id_aporte_uuid", "STRING"),
                    bigquery.SchemaField("fundo_origem_id", "STRING"),
                    bigquery.SchemaField("nome_fundo_investidor", "STRING"),
                    bigquery.SchemaField("empresa_sacada_nome", "STRING"),
                    bigquery.SchemaField("cnpj_sacado_limpo", "STRING"),
                    bigquery.SchemaField("valor_aporte_compra", "FLOAT"),
                    bigquery.SchemaField("valor_mercado_atual", "FLOAT"),
                    bigquery.SchemaField("taxa_retorno_pre_fixada", "FLOAT"),
                    bigquery.SchemaField("prazo_vencimento_dias", "INTEGER"),
                    bigquery.SchemaField("quantidade_papeis_adquiridos", "INTEGER"),
                    bigquery.SchemaField("score_risco_interno", "FLOAT"),
                    bigquery.SchemaField("status_prazo_vencimento", "STRING"),
                    bigquery.SchemaField("bloco_liquidez_setorial", "STRING"),
                    bigquery.SchemaField("categoria_tecnica_ativo", "STRING"),
                    bigquery.SchemaField("codigo_identificacao_isin", "STRING"),
                    bigquery.SchemaField("codigo_identificacao_selic", "STRING"),
                    bigquery.SchemaField("data_referencia_competencia", "DATE"),
                ],
                # Se a tabela já existe, insere as novas linhas ao final
                write_disposition="WRITE_APPEND", 
            )

            # Dispara a carga de dados
            job = client.load_table_from_dataframe(
                dataframe_bigquery, table_id, job_config=job_config
            )
            
            # Aguarda a conclusão da operação
            job.result()  
            print(f"Dados inseridos com sucesso na {table_id}.")

        except Exception as e:
            print(f"Falha ao enviar para o BigQuery: {e}")