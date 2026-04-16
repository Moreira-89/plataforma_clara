import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Nomes exatos das colunas que o sistema espera no arquivo (cabeçalho do CSV)
COLUNAS_OBRIGATORIAS: list[str] = [
    "fundo_origem_id",
    "nome_fundo_investidor",
    "empresa_sacada_nome",
    "cnpj_sacado_limpo",
    "valor_aporte_compra",
    "valor_mercado_atual",
    "taxa_retorno_pre_fixada",
    "prazo_vencimento_dias",
    "quantidade_papeis_adquiridos",
    "score_risco_interno",
    "status_prazo_vencimento",
    "bloco_liquidez_setorial",
    "categoria_tecnica_ativo",
    "codigo_identificacao_isin",
    "codigo_identificacao_selic",
    "data_referencia_competencia",
]

# Colunas cuja ausência de valor torna a linha inutilizável
_COLUNAS_CRITICAS: list[str] = ["cnpj_sacado_limpo", "valor_aporte_compra"]


def processar_arquivo_csv(caminho_arquivo: str | object) -> pd.DataFrame:
    """
    Lê um CSV do disco, valida o esquema e devolve apenas dados utilizáveis.

    Args:
        caminho_arquivo: Caminho do arquivo CSV a ser processado.

    Returns:
        DataFrame com as colunas obrigatórias, sem linhas que tenham
        ``cnpj_sacado_limpo`` ou ``valor_aporte_compra`` nulos.

    Raises:
        ValueError: Se o arquivo for inválido ou faltar colunas obrigatórias.
    """
    try:
        dataframe = pd.read_csv(caminho_arquivo)
    except Exception as exc:
        logger.error("Falha ao ler CSV '%s': %s", caminho_arquivo, exc)
        raise ValueError(
            "O formato do arquivo CSV é inválido. Por favor, envie um .csv válido!"
        ) from exc

    # Comparar o que veio no arquivo com o contrato fixo do sistema
    colunas_presentes = set(dataframe.columns)
    colunas_faltantes = [
        col for col in COLUNAS_OBRIGATORIAS if col not in colunas_presentes
    ]

    if colunas_faltantes:
        logger.warning("CSV com colunas faltantes: %s", colunas_faltantes)
        raise ValueError(
            f"O CSV está fora do padrão. Colunas ausentes: {', '.join(colunas_faltantes)}"
        )

    # Seleciona só as colunas do padrão (descarta extras) e remove linhas
    # onde as colunas críticas estejam nulas.
    dataframe_limpo = dataframe[COLUNAS_OBRIGATORIAS].dropna(subset=_COLUNAS_CRITICAS)

    logger.info(
        "CSV processado: %d linhas válidas de %d totais.",
        len(dataframe_limpo),
        len(dataframe),
    )

    return dataframe_limpo
