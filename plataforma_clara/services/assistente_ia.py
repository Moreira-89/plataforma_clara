import logging
from typing import Any

logger = logging.getLogger(__name__)


def gerar_insight_relatorio_langchain(dados_bloco_liquidez: dict[str, Any]) -> str:
    """
    CONTRATO DO LLM:
    Recebe o consolidado financeiro de um bloco.
    Deve retornar um parágrafo de texto interpretando o risco/saúde do fundo.

    Args:
        dados_bloco_liquidez: Dicionário com métricas agregadas de um bloco.

    Returns:
        String com o insight gerado (atualmente um mock).
    """
    # TODO (Time LangChain): Inserir a lógica de inicialização do ChatOpenAI / GoogleGenerativeAI
    # e a cadeia (chain) de prompts aqui.

    logger.info("[MOCK] Chamando o assistente de IA para bloco: %s", dados_bloco_liquidez.get("bloco_liquidez_setorial", "N/A"))

    insight_falso = (
        "Com base nos dados analisados, o Bloco Safira apresenta uma liquidez "
        "excelente. 92% das empresas sacadas mantêm um Score de Reputação acima "
        "da média do mercado, sugerindo baixo risco de inadimplência no curto prazo."
    )

    return insight_falso