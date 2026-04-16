import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv

def buscar_metricas_blocos_liquidez() -> dict:
    """
    Conecta no BigQuery e retorna um resumo financeiro e de risco
    agrupado por Bloco de Liquidez para alimentar os gráficos do Dashboard.
    """
    load_dotenv()
    
    try:
        client = bigquery.Client()
        
        # Essa query faz o trabalho pesado na nuvem: 
        # Agrupa pelos blocos, soma o dinheiro e tira a média do score.
        query = """
            SELECT 
                bloco_liquidez_setorial,
                SUM(valor_mercado_atual) as total_alocado,
                AVG(score_risco_interno) as score_medio_reputacao,
                COUNT(id_aporte_uuid) as quantidade_aportes
            FROM `plataforma-clara.dados_fidc.tb_aporte`
            WHERE bloco_liquidez_setorial IS NOT NULL
            GROUP BY bloco_liquidez_setorial
            ORDER BY total_alocado DESC
        """
        
        # O BigQuery tem um método nativo maravilhoso que já devolve um DataFrame Pandas
        dataframe = client.query(query).to_dataframe()
        
        # Preenche possíveis valores nulos com zero para não quebrar os gráficos
        dataframe.fillna(0, inplace=True)
        
        # Convertendo para dicionário (lista de dicts) para trafegar seguro no Reflex
        dados_dashboard = dataframe.to_dict(orient="records")
        
        return dados_dashboard
        
    except Exception as e:
        print(f"Erro ao buscar métricas no BigQuery: {e}")
        # Retorna uma lista vazia em caso de erro para não travar a tela
        return []