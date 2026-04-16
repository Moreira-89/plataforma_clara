import os
import joblib
import pandas as pd

def calcular_score_reputacao(cnpj_empresa: str, dados_historicos: dict) -> float:
    """
    CONTRATO DO MODELO: 
    Recebe o CNPJ e os dados da empresa.
    Deve retornar um Score do tipo float (ex: de 0.0 a 100.0).
    """
    
    # TODO (Time de ML): Substituir este bloco pelo carregamento do .pkl
    # caminho_modelo = os.path.join(os.getcwd(), 'modelos', 'modelo_reputacao_v1.pkl')
    # modelo = joblib.load(caminho_modelo)
    # predição = modelo.predict(dados_formatados)
    
    print(f"[MOCK] Simulando cálculo de score para o CNPJ: {cnpj_empresa}")
    
    # Retornamos um dado estático (Mock) para você já conseguir testar o visual do Dashboard
    score_falso = 87.5 
    
    return score_falso