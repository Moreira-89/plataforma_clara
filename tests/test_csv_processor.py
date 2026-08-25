"""
Testes de caracterização do processamento de CSV de aportes.

Cobre `services/csv_processor.processar_arquivo_csv`, a porta de entrada de todos
os dados da plataforma. Este é o módulo mais crítico da suíte: é o único ponto do
sistema onde dados externos não confiáveis viram registros de banco.

COMO FUNCIONA:
    1. Contrato de schema — colunas ausentes derrubam o arquivo inteiro; colunas
       extras são silenciosamente descartadas.
    2. Descarte de linhas — linhas com dados críticos, numéricos ou de data inválidos
       são removidas SEM erro; o restante do arquivo é processado normalmente.
    3. Normalização — documentos perdem formatação; datas viram `datetime.date`.
"""

from __future__ import annotations

import datetime
from typing import Any

import pandas as pd
import pytest

from plataforma_clara.services.csv_processor import (
    COLUNAS_OBRIGATORIAS,
    processar_arquivo_csv,
)

# -----------------------------------------------------------------------------
# CONTRATO DE SCHEMA
# -----------------------------------------------------------------------------


def test_csv_valido_preserva_todas_as_linhas(escrever_csv, linha_aporte_valida):
    """O caminho feliz: nenhuma linha válida pode ser perdida."""
    caminho = escrever_csv([linha_aporte_valida, linha_aporte_valida])

    resultado = processar_arquivo_csv(caminho)

    assert len(resultado) == 2
    assert list(resultado.columns) == COLUNAS_OBRIGATORIAS


def test_coluna_ausente_derruba_o_arquivo_inteiro(escrever_csv, linha_aporte_valida):
    """
    Falta de coluna obrigatória é erro de contrato, não de linha: o arquivo todo é
    rejeitado. A mensagem nomeia as colunas ausentes porque ela chega ao usuário final.
    """
    sem_score = {k: v for k, v in linha_aporte_valida.items() if k != "score_risco_interno"}
    caminho = escrever_csv([sem_score])

    with pytest.raises(ValueError, match="score_risco_interno"):
        processar_arquivo_csv(caminho)


def test_colunas_extras_sao_descartadas(escrever_csv, linha_aporte_valida):
    """Colunas fora do contrato não podem vazar para o banco."""
    with_extra: dict[str, Any] = dict(linha_aporte_valida)
    with_extra["coluna_inventada"] = "valor qualquer"
    caminho = escrever_csv([with_extra])

    resultado = processar_arquivo_csv(caminho)

    assert "coluna_inventada" not in resultado.columns
    assert list(resultado.columns) == COLUNAS_OBRIGATORIAS


def test_arquivo_ilegivel_vira_value_error(tmp_path):
    """
    Qualquer falha de leitura vira ValueError com mensagem amigável — o state de
    ingestão exibe `str(e)` direto na tela para o usuário da gestora.
    """
    caminho = tmp_path / "inexistente.csv"

    with pytest.raises(ValueError, match="csv"):
        processar_arquivo_csv(caminho)


# -----------------------------------------------------------------------------
# DESCARTE DE LINHAS INVÁLIDAS
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "campo",
    ["cnpj_sacado_limpo", "valor_aporte_compra", "documento_investidor_cpf_cnpj"],
)
def test_linha_sem_campo_critico_e_descartada(escrever_csv, linha_aporte_valida, campo):
    """
    As 3 colunas críticas tornam a linha inutilizável quando vazias: sem elas não é
    possível atribuir o aporte a um investidor nem a um sacado.
    """
    invalida = dict(linha_aporte_valida)
    invalida[campo] = ""
    caminho = escrever_csv([linha_aporte_valida, invalida])

    resultado = processar_arquivo_csv(caminho)

    assert len(resultado) == 1


def test_linha_invalida_nao_contamina_as_demais(escrever_csv, linha_aporte_valida):
    """
    Decisão de produto embutida no código: um CSV parcialmente ruim é aceito e as
    linhas boas são gravadas. Não há rejeição do lote inteiro nem relatório do que caiu.
    """
    ruim = dict(linha_aporte_valida, valor_aporte_compra="não é número")
    caminho = escrever_csv([linha_aporte_valida, ruim, linha_aporte_valida])

    resultado = processar_arquivo_csv(caminho)

    assert len(resultado) == 2


def test_data_invalida_descarta_a_linha(escrever_csv, linha_aporte_valida):
    """Datas não parseáveis viram NaT e a linha cai — não vira NULL no banco."""
    caminho = escrever_csv([dict(linha_aporte_valida, data_vencimento="31/02/2026")])

    resultado = processar_arquivo_csv(caminho)

    assert len(resultado) == 0


def test_string_apenas_com_espacos_conta_como_vazia(escrever_csv, linha_aporte_valida):
    """
    "   " não é nulo para o Pandas por padrão. O processador força esse caso a nulo
    antes de validar, senão um CNPJ em branco passaria pela validação de presença.
    """
    caminho = escrever_csv([dict(linha_aporte_valida, cnpj_sacado_limpo="   ")])

    resultado = processar_arquivo_csv(caminho)

    assert len(resultado) == 0


def test_csv_inteiramente_invalido_devolve_dataframe_vazio(escrever_csv, linha_aporte_valida):
    """
    Zero linhas válidas NÃO é erro — devolve DataFrame vazio. Quem trata isso é o
    IngestaoDadosState, que mostra "sem linhas válidas para inserção".
    """
    caminho = escrever_csv([dict(linha_aporte_valida, documento_investidor_cpf_cnpj="")])

    resultado = processar_arquivo_csv(caminho)

    assert len(resultado) == 0
    assert list(resultado.columns) == COLUNAS_OBRIGATORIAS


# -----------------------------------------------------------------------------
# NORMALIZAÇÃO E TIPOS
# -----------------------------------------------------------------------------


def test_documentos_perdem_formatacao(escrever_csv, linha_aporte_valida):
    """
    CPF/CNPJ são normalizados para só dígitos. Isso é o que permite o filtro SQL
    comparar com o documento da sessão, que também é normalizado no login.
    """
    caminho = escrever_csv(
        [
            dict(
                linha_aporte_valida,
                documento_investidor_cpf_cnpj="123.456.789-01",
                cnpj_sacado_limpo="12.345.678/0001-99",
            )
        ]
    )

    resultado = processar_arquivo_csv(caminho)

    assert resultado.iloc[0]["documento_investidor_cpf_cnpj"] == "12345678901"
    assert resultado.iloc[0]["cnpj_sacado_limpo"] == "12345678000199"


def test_cnpj_com_zero_a_esquerda_nao_vira_numero(escrever_csv, linha_aporte_valida):
    """
    Regressão clássica de Pandas: sem dtype explícito, "00123..." viraria int e
    perderia o zero à esquerda, quebrando o vínculo com o sacado.
    """
    caminho = escrever_csv([dict(linha_aporte_valida, cnpj_sacado_limpo="00123456000199")])

    resultado = processar_arquivo_csv(caminho)

    assert resultado.iloc[0]["cnpj_sacado_limpo"] == "00123456000199"


def test_datas_viram_objetos_date(escrever_csv, linha_aporte_valida):
    """O SQLModel espera `datetime.date` nas colunas de data, não string nem Timestamp."""
    caminho = escrever_csv([linha_aporte_valida])

    resultado = processar_arquivo_csv(caminho)

    assert resultado.iloc[0]["data_vencimento"] == datetime.date(2026, 12, 31)
    assert isinstance(resultado.iloc[0]["data_vencimento"], datetime.date)


def test_isin_ausente_nao_descarta_a_linha(escrever_csv, linha_aporte_valida):
    """
    `codigo_identificacao_isin` é a única coluna opcional do contrato: nem todo ativo
    tem ISIN. A linha sobrevive ao processamento, como esperado.
    """
    caminho = escrever_csv([dict(linha_aporte_valida, codigo_identificacao_isin="")])

    resultado = processar_arquivo_csv(caminho)

    assert len(resultado) == 1
    assert pd.isna(resultado.iloc[0]["codigo_identificacao_isin"])


def test_isin_ausente_vira_pd_na_e_nao_none(escrever_csv, linha_aporte_valida):
    """
    CARACTERIZAÇÃO DE BUG (D12 no roadmap) — este teste documenta comportamento
    QUEBRADO, não desejado. Não "consertar" o teste sem consertar o código.

    A etapa 8 do processador troca NaN por None justamente porque o psycopg2 não
    adapta NaN. Mas a etapa 4 converteu as colunas de texto para o dtype "string"
    do Pandas, e uma coluna StringDtype não armazena None: ela guarda `pd.NA`.
    O `.where(pd.notnull(df), None)` da etapa 8 portanto não tem efeito aqui.

    Consequência prática: `psycopg2.extensions.adapt(pd.NA)` levanta
    ProgrammingError("can't adapt type 'NAType'"), então um único aporte sem ISIN
    derruba o `bulk_insert_mappings` do lote INTEIRO na ingestão.

    Quando o bug for corrigido (provavelmente na Fase 1, ao extrair o domínio),
    este teste deve ser trocado por uma asserção de `is None`.
    """
    caminho = escrever_csv([dict(linha_aporte_valida, codigo_identificacao_isin="")])

    resultado = processar_arquivo_csv(caminho)
    valor = resultado.iloc[0]["codigo_identificacao_isin"]

    assert valor is pd.NA
    assert valor is not None
