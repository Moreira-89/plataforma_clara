"""
Serviço responsável pelo processamento e validação de arquivos CSV de aportes.

Recebe o caminho de um arquivo CSV, valida que todas as colunas obrigatórias do
contrato da plataforma estão presentes, normaliza os dados e devolve um DataFrame
limpo e pronto para persistência no banco.
"""

import logging

import pandas as pd

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# Nomes exatos das colunas que o sistema espera no arquivo (contrato fixo do CSV).
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
    "flag_outlier_valor",
]

# Colunas cuja ausência de valor torna a linha inteiramente inutilizável.
_COLUNAS_CRITICAS: list[str] = [
    "cnpj_sacado_limpo",
    "valor_aporte_compra",
    "documento_investidor_cpf_cnpj",
]

# Colunas que devem ser convertidas para float; linhas inválidas são descartadas.
_COLUNAS_NUMERICAS: list[str] = [
    "valor_aporte_compra",
    "valor_mercado_atual",
    "quantidade_papeis_adquiridos",
    "prazo_vencimento_dias",
    "taxa_retorno_pre_fixada",
    "score_risco_interno",
]

# Colunas de data que precisam ser convertidas para datetime.date.
_COLUNAS_DATA: list[str] = ["data_vencimento", "data_referencia_competencia"]


# -----------------------------------------------------------------------------
# PROCESSAMENTO PRINCIPAL
# -----------------------------------------------------------------------------


def processar_arquivo_csv(caminho_arquivo: str | object) -> pd.DataFrame:
    """
    Lê um CSV do disco, valida o esquema e devolve apenas os dados utilizáveis.

    COMO FUNCIONA:
        1. Leitura do CSV — Usa pd.read_csv com dtypes explícitos para evitar que
           o Pandas tente inferir tipos incorretos (ex: CNPJ virar inteiro).
        2. Validação de Schema — Compara as colunas do arquivo com COLUNAS_OBRIGATORIAS.
           Qualquer coluna faltante lança ValueError com lista das ausentes.
        3. Seleção e Cópia — Mantém apenas as colunas do contrato e descarta extras,
           garantindo que colunas inesperadas não entrem no banco.
        4. Tratamento de Strings Vazias — Strings com só espaços são tratadas como
           nulas antes de qualquer validação de presença.
        5. Normalização de Documentos — Remove caracteres não numéricos de CPF/CNPJ
           para garantir comparação uniforme nos filtros SQL.
        6. Conversão de Tipos — Converte colunas numéricas com pd.to_numeric(errors="coerce")
           e datas com pd.to_datetime(errors="coerce"), transformando inválidos em NaN/NaT.
        7. Descarte de Linhas Inválidas — Remove linhas com nulos nas colunas críticas,
           numéricas e de data.
        8. Substituição de NaN por None — Necessário para que o SQLModel insira NULL
           corretamente no PostgreSQL (NaN não é reconhecido como NULL pelo driver).

    Args:
        caminho_arquivo (str | object): Caminho do arquivo CSV a ser processado.
                                        Aceita string ou objeto Path.

    Returns:
        pd.DataFrame: DataFrame com apenas as colunas obrigatórias e linhas válidas.

    Raises:
        ValueError: Se o arquivo não for um CSV válido ou se faltar colunas obrigatórias.
    """
    # --- 1. LEITURA DO CSV ---
    # Definimos dtypes explícitos para as colunas de texto para evitar que o Pandas
    # converta CNPJs (strings numéricas longas) para int/float e perca zeros à esquerda.
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
            "flag_outlier_valor": str,
        }
        dataframe = pd.read_csv(caminho_arquivo, dtype=dtypes)
    except Exception as exc:
        logger.error("Falha ao ler CSV '%s': %s", caminho_arquivo, exc)
        raise ValueError(
            "O formato do arquivo CSV é inválido. Por favor, envie um .csv válido!"
        ) from exc

    # --- 2. VALIDAÇÃO DE SCHEMA ---
    colunas_presentes = set(dataframe.columns)
    colunas_faltantes = [col for col in COLUNAS_OBRIGATORIAS if col not in colunas_presentes]

    if colunas_faltantes:
        logger.warning("CSV com colunas faltantes: %s", colunas_faltantes)
        raise ValueError(
            f"O CSV está fora do padrão. Colunas ausentes: {', '.join(colunas_faltantes)}"
        )

    # --- 3. SELEÇÃO E CÓPIA ---
    # .copy() evita SettingWithCopyWarning ao modificar o DataFrame filtrado.
    dataframe_limpo = dataframe[COLUNAS_OBRIGATORIAS].copy()

    # --- 4. TRATAMENTO DE STRINGS VAZIAS ---
    # Strings com apenas espaços ("  ") não são detectadas como nulas por padrão,
    # então convertemos para pd.NA antes de qualquer validação.
    for col in dataframe_limpo.select_dtypes(include=["object", "string"]).columns:
        serie = dataframe_limpo[col].astype("string")
        dataframe_limpo[col] = serie.mask(serie.str.strip() == "", pd.NA)

    # --- 5. NORMALIZAÇÃO DE DOCUMENTOS ---
    # Remove pontos, traços e barras de CPF/CNPJ para garantir uniformidade
    # ao comparar com valores armazenados no banco (somente dígitos).
    dataframe_limpo["documento_investidor_cpf_cnpj"] = (
        dataframe_limpo["documento_investidor_cpf_cnpj"]
        .astype("string")
        .str.replace(r"[^0-9]", "", regex=True)
    )
    dataframe_limpo["cnpj_sacado_limpo"] = (
        dataframe_limpo["cnpj_sacado_limpo"]
        .astype("string")
        .str.replace(r"[^0-9]", "", regex=True)
    )

    # --- 6. CONVERSÃO DE TIPOS ---
    # errors="coerce" transforma valores não numéricos em NaN, que serão
    # removidos na etapa 7 junto com as linhas críticas ausentes.
    for col in _COLUNAS_NUMERICAS:
        dataframe_limpo[col] = pd.to_numeric(dataframe_limpo[col], errors="coerce")

    for col in _COLUNAS_DATA:
        dataframe_limpo[col] = pd.to_datetime(dataframe_limpo[col], errors="coerce").dt.date

    # --- 7. DESCARTE DE LINHAS INVÁLIDAS ---
    dataframe_limpo = dataframe_limpo.dropna(
        subset=_COLUNAS_CRITICAS + _COLUNAS_NUMERICAS + _COLUNAS_DATA
    )

    # --- 8. SUBSTITUIÇÃO DE NaN POR None ---
    # O psycopg2 (driver PostgreSQL) não aceita float("nan") como NULL.
    # pd.notnull retorna False para NaN e NaT, então where() substitui por None.
    dataframe_limpo = dataframe_limpo.where(pd.notnull(dataframe_limpo), None)

    logger.info(
        "CSV processado: %d linhas válidas de %d totais.",
        len(dataframe_limpo),
        len(dataframe),
    )

    return dataframe_limpo
