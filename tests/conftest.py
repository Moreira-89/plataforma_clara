"""
Fixtures compartilhadas pela suíte de testes da Plataforma Clara.

Esta suíte é de *caracterização*: ela documenta o comportamento ATUAL do código
em Reflex, incluindo comportamentos discutíveis. O objetivo não é afirmar que o
comportamento está correto, e sim detectar quando ele muda durante a migração
para FastAPI. Se um teste quebrar numa refatoração, a pergunta é "a mudança foi
intencional?", não necessariamente "o código novo está errado?".

COMO FUNCIONA:
    1. Dados de exemplo — `linha_aporte_valida` devolve um registro de aporte que
       passa em todas as validações do csv_processor. Testes derivam variações dele.
    2. Fábrica de CSV — `escrever_csv` grava uma lista de dicts num arquivo temporário
       e devolve o caminho, isolando cada teste em seu próprio tmp_path.
    3. Sessão falsa de banco — `fabricar_sessao_fake` substitui `rx.session()` por um
       context manager que devolve linhas pré-definidas, sem tocar em Postgres.
    4. Reset de cache — `limpar_caches_dashboard` (autouse) zera os caches globais de
       módulo entre testes, já que eles sobrevivem ao fim de cada teste.
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


# -----------------------------------------------------------------------------
# BANCO DE DADOS FALSO
# -----------------------------------------------------------------------------


class _ResultadoFake:
    """Imita o encadeamento `session.execute(...).mappings().fetchall()` do SQLAlchemy."""

    def __init__(self, linhas: list[dict[str, Any]]):
        self._linhas = linhas

    def mappings(self) -> _ResultadoFake:
        return self

    def fetchall(self) -> list[dict[str, Any]]:
        return self._linhas


class SessaoFake:
    """
    Sessão de banco falsa: devolve linhas pré-definidas e registra as chamadas.

    Atributos:
        chamadas: lista de (query, params) recebidos — permite asserção sobre
                  quantas vezes o banco foi consultado (essencial para testar cache).
    """

    def __init__(self, linhas: list[dict[str, Any]], erro: Exception | None = None):
        self._linhas = linhas
        self._erro = erro
        self.chamadas: list[tuple[Any, Any]] = []

    def __enter__(self) -> SessaoFake:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def execute(self, query: Any, params: Any = None) -> _ResultadoFake:
        self.chamadas.append((query, params))
        if self._erro is not None:
            raise self._erro
        return _ResultadoFake(self._linhas)


@pytest.fixture
def fabricar_sessao_fake() -> Callable[..., Callable[[], SessaoFake]]:
    """
    Devolve uma fábrica de substitutos para `rx.session`.

    Uso típico:
        sessao = SessaoFake([...])
        monkeypatch.setattr(dashboard_service.rx, "session", lambda: sessao)

    A fábrica devolve sempre a MESMA instância de SessaoFake, para que o teste
    possa inspecionar `sessao.chamadas` e contar os acessos ao banco.
    """

    def _fabricar(
        linhas: list[dict[str, Any]] | None = None, *, erro: Exception | None = None
    ) -> Callable[[], SessaoFake]:
        sessao = SessaoFake(linhas or [], erro=erro)
        return lambda: sessao

    return _fabricar


# -----------------------------------------------------------------------------
# ISOLAMENTO DE ESTADO GLOBAL
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def limpar_caches_dashboard() -> None:
    """
    Zera os caches de módulo do dashboard_service antes de cada teste.

    Os caches são variáveis globais com TTL de 5 minutos (D4 no roadmap). Sem este
    reset, um teste contaminaria o seguinte — e a ordem de execução mudaria o resultado.
    O import é preguiçoso porque o dashboard_service importa reflex, que nem todo
    teste precisa carregar.
    """
    try:
        from plataforma_clara.services import dashboard_service
    except ImportError:  # pragma: no cover - ambiente sem reflex instalado
        return

    dashboard_service._cache_investidor.clear()
    dashboard_service._cache_gestora = []
    dashboard_service._cache_gestora_timestamp = 0.0
    dashboard_service._cache_tabela_aportes = []
    dashboard_service._cache_tabela_aportes_timestamp = 0.0
