import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Nomes exatos das colunas que o sistema espera no arquivo (cabeçalho do CSV)
COLUNAS_OBRIGATORIAS: list[str] = [
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

# Colunas cuja ausência de valor torna a linha inutilizável
_COLUNAS_CRITICAS: list[str] = ["cnpj_sacado_limpo", "valor_aporte_compra", "documento_investidor_cpf_cnpj"]


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
        dtypes = {
            "id_aporte_uuid": str,
            "documento_investidor_cpf_cnpj": str,
            "fundo_origem_id": str,
            "nome_fundo_investidor": str,
            "empresa_sacada_nome": str,
            "cnpj_sacado_limpo": str,
            "status_prazo_vencimento": str,
            "bloco_liquidez_setorial": str,
            "categoria_tecnica_ativo": str,
            "codigo_identificacao_isin": str,
            "flag_outlier_valor": str
        }
        dataframe = pd.read_csv(caminho_arquivo, dtype=dtypes)
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

    # Converte colunas de data para objetos datetime.date para compatibilidade com o banco de dados
    for col in ["data_vencimento", "data_referencia_competencia"]:
        if col in dataframe_limpo.columns:
            dataframe_limpo[col] = pd.to_datetime(dataframe_limpo[col]).dt.date

    # Substitui NaN por None para que o SQLModel/PostgreSQL insiram como NULL corretamente
    dataframe_limpo = dataframe_limpo.where(pd.notnull(dataframe_limpo), None)

    logger.info(
        "CSV processado: %d linhas válidas de %d totais.",
        len(dataframe_limpo),
        len(dataframe),
    )

    return dataframe_limpo
