import logging
from typing import Any

logger = logging.getLogger(__name__)


def calcular_score_reputacao(cnpj_empresa: str, dados_historicos: dict[str, Any]) -> float:
    """
    CONTRATO DO MODELO:
    Recebe o CNPJ e os dados da empresa.
    Deve retornar um Score do tipo float (ex: de 0.0 a 100.0).

    Args:
        cnpj_empresa: CNPJ da empresa a ser avaliada.
        dados_historicos: Dicionário com dados históricos da empresa.

    Returns:
        Score de reputação como float.
    """
    # TODO (Time de ML): Substituir este bloco pelo carregamento do .pkl
    # caminho_modelo = os.path.join(os.getcwd(), 'modelos', 'modelo_reputacao_v1.pkl')
    # modelo = joblib.load(caminho_modelo)
    # predição = modelo.predict(dados_formatados)

    logger.info("[MOCK] Simulando cálculo de score para o CNPJ: %s", cnpj_empresa)

    # Retornamos um dado estático (Mock) para testar o visual do Dashboard
    score_falso = 87.5

    return score_falso