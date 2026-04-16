import pandas as pd

# Nomes exatos das colunas que o sistema espera no arquivo (cabeçalho do CSV)
COLUNAS_OBRIGATORIAS = [
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
    "data_referencia_competencia"
]


def processar_arquivo_csv(caminho_arquivo):
    """
    Lê um CSV do disco, valida o esquema e devolve apenas dados utilizáveis.

    Args:
        caminho_arquivo: Caminho do arquivo CSV a ser processado.

    Returns:
        DataFrame com as colunas obrigatórias.
    """
    # pd.read_csv pode falhar por encoding, arquivo quebrado, formato não tabular, etc.
    try:
        # delimiter padrão é vírgula; primeira linha vira nome das colunas
        dataframe = pd.read_csv(caminho_arquivo)
    except Exception:
        # Unifica falhas de leitura numa única mensagem para a camada de API/UI
        raise ValueError("O formato do arquivo CSV é inválido. Por favor, envie um .csv válido!")

    # Comparar o que veio no arquivo com o contrato fixo do sistema
    colunas_presentes = dataframe.columns.tolist()

    # Lista de colunas obrigatórias que não existem em colunas_presentes
    colunas_faltantes = [coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in colunas_presentes]

    if colunas_faltantes:
        # Lista nomes separados por vírgula para o usuário corrigir o modelo do CSV
        raise ValueError(f"O CSV está fora do padrão. Colunas ausentes: {', '.join(colunas_faltantes)}")

    # Seleciona só as colunas do padrão (descarta colunas extras sem erro) e limpa linhas ruins
    dataframe_limpo = dataframe[COLUNAS_OBRIGATORIAS].dropna(subset=["cnpj", "valor_aporte"])
    # subset= restringe o dropna a essas colunas: outras células vazias permanecem como NaN

    return dataframe_limpo
