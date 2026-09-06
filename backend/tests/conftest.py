"""
Fixtures compartilhadas pela suíte de testes da Plataforma Clara.

Esta suíte é de *caracterização*: documenta o comportamento ATUAL, inclusive o
discutível. Se um teste quebrar numa refatoração, a pergunta é "a mudança foi
intencional?", não necessariamente "o código novo está errado?".

COMO FUNCIONA:
    1. Dados de exemplo — `linha_aporte_valida` devolve um registro de aporte que
       passa em todas as validações do csv_processor. Testes derivam variações dele.
    2. Fábrica de CSV — `escrever_csv` grava uma lista de dicts num arquivo temporário
       e devolve o caminho, isolando cada teste em seu próprio tmp_path.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# -----------------------------------------------------------------------------
# DADOS DE EXEMPLO
# -----------------------------------------------------------------------------

# Espelha as 19 colunas exigidas por services/csv_processor.COLUNAS_OBRIGATORIAS.
_APORTE_BASE: dict[str, Any] = {
    "id_aporte_uuid": "11111111-1111-4111-8111-111111111111",
    "documento_investidor_cpf_cnpj": "12345678901",
    "fundo_origem_id": "FIDC-001",
    "nome_fundo_investidor": "Fundo Exemplo FIDC",
    "empresa_sacada_nome": "Empresa Sacada LTDA",
    "cnpj_sacado_limpo": "12345678000199",
    "valor_aporte_compra": "1000.50",
    "valor_mercado_atual": "1050.75",
    "quantidade_papeis_adquiridos": "10",
    "data_vencimento": "2026-12-31",
    "data_referencia_competencia": "2026-08-01",
    "prazo_vencimento_dias": "120",
    "status_prazo_vencimento": "Vigente",
    "taxa_retorno_pre_fixada": "12.5",
    "bloco_liquidez_setorial": "Safira",
    "categoria_tecnica_ativo": "Recebível Comercial",
    "codigo_identificacao_isin": "BRXXXXCTF001",
    "score_risco_interno": "78.4",
    "flag_outlier_valor": "NAO",
}


@pytest.fixture
def linha_aporte_valida() -> dict[str, Any]:
    """Um registro de aporte que sobrevive a todas as validações do csv_processor."""
    return dict(_APORTE_BASE)


@pytest.fixture
def escrever_csv(tmp_path: Path) -> Callable[..., Path]:
    """
    Fábrica que grava linhas num CSV temporário e devolve o caminho.

    Args:
        linhas: lista de dicts, um por linha do CSV.
        colunas: cabeçalho explícito. Se omitido, usa as chaves da primeira linha —
                 útil para simular CSVs com colunas faltantes ou extras.
        nome: nome do arquivo gerado.

    Returns:
        Path: caminho do CSV escrito em tmp_path.
    """

    def _escrever(
        linhas: list[dict[str, Any]],
        *,
        colunas: list[str] | None = None,
        nome: str = "aportes.csv",
    ) -> Path:
        caminho = tmp_path / nome
        cabecalho = colunas if colunas is not None else list(linhas[0].keys())

        with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=cabecalho, extrasaction="ignore")
            escritor.writeheader()
            escritor.writerows(linhas)

        return caminho

    return _escrever
