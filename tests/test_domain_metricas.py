"""
Testes das regras de negócio dos dashboards.

Cobre `domain/metricas.py` — as regras que a camada de entrega consome prontas.

O que estes testes travam é a MATEMÁTICA que o investidor vê: consolidação de KPIs,
peso de cada empresa no bloco e as faixas dos filtros. Um erro aqui produz uma tela
plausível e errada, que é o pior tipo de erro num produto de transparência.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic", reason="requer pydantic instalado")

from plataforma_clara.domain import metricas  # noqa: E402
from plataforma_clara.domain.schemas import AgregadoEmpresa, MetricaBloco  # noqa: E402


def _bloco(nome: str, total: float, score: float, aportes: int = 1) -> MetricaBloco:
    return MetricaBloco(
        bloco_liquidez_setorial=nome,
        total_alocado=total,
        score_medio_reputacao=score,
        quantidade_aportes=aportes,
    )


def _empresa(nome: str, valor: float, score: float, prazo: float = 0.0) -> AgregadoEmpresa:
    return AgregadoEmpresa(
        empresa_sacada_nome=nome,
        cnpj_sacado_limpo="12345678000199",
        valor_total_alocado=valor,
        score_medio=score,
        prazo_medio_dias=prazo,
    )


# -----------------------------------------------------------------------------
# CONSOLIDAÇÃO DE KPIs
# -----------------------------------------------------------------------------


def test_kpis_somam_valores_e_aportes():
    """Total alocado e quantidade de aportes são somas simples entre os blocos."""
    kpis = metricas.consolidar_kpis(
        [_bloco("Safira", 100.0, 80.0, 3), _bloco("Rubi", 300.0, 60.0, 2)]
    )

    assert kpis.total_alocado == 400.0
    assert kpis.quantidade_aportes == 5


def test_score_medio_e_media_simples_nao_ponderada():
    """
    CARACTERIZAÇÃO DE DECISÃO DISCUTÍVEL: o score consolidado é a média das médias
    por bloco, sem peso pelo volume. Um bloco de R$ 1 com score 100 pesa o mesmo que
    um de R$ 1 milhão com score 40 — aqui a média dá 70, não os ~40 que a carteira
    de fato tem. Comportamento anterior à Fase 1, preservado.
    """
    kpis = metricas.consolidar_kpis(
        [_bloco("Micro", 1.0, 100.0), _bloco("Grande", 1_000_000.0, 40.0)]
    )

    assert kpis.score_medio == 70.0


def test_kpis_de_lista_vazia_sao_zerados():
    """Dashboard sem dados mostra zeros, nunca uma divisão por zero."""
    kpis = metricas.consolidar_kpis([])

    assert (kpis.total_alocado, kpis.score_medio, kpis.quantidade_aportes) == (0.0, 0.0, 0)


# -----------------------------------------------------------------------------
# TABELA DA GESTORA
# -----------------------------------------------------------------------------


def test_tabela_da_gestora_traduz_score_em_nota_e_status():
    """A regra que saiu do `CASE WHEN` do SQL na Fase 1."""
    linhas = metricas.montar_tabela_gestora([_empresa("Empresa A", 1000.0, 45.0)])

    assert linhas[0].risco == "B"
    assert linhas[0].status == "Atenção"
    assert linhas[0].valor == "R$ 1.000,00"
    assert linhas[0].cnpj == "12.345.678/0001-99"


# -----------------------------------------------------------------------------
# FILTROS DE BLOCOS
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# DETALHES DO BLOCO
# -----------------------------------------------------------------------------


def test_detalhe_calcula_peso_de_cada_empresa_no_bloco():
    """O peso é a fatia da empresa no volume total — a soma precisa fechar em 100%."""
    detalhe = metricas.montar_detalhe_bloco(
        "Safira", [_empresa("A", 750.0, 80.0), _empresa("B", 250.0, 60.0)]
    )

    assert [empresa.peso for empresa in detalhe.empresas] == ["75.0%", "25.0%"]
    assert detalhe.volume_total == "R$ 1.000,00"


def test_detalhe_arredonda_prazo_medio_para_baixo():
    """O prazo é exibido em dias inteiros — 119.7 dias vira '119 Dias'."""
    detalhe = metricas.montar_detalhe_bloco("Safira", [_empresa("A", 100.0, 80.0, prazo=119.7)])

    assert detalhe.prazo_medio == "119 Dias"


def test_bloco_sem_empresas_devolve_detalhe_vazio():
    """Bloco inexistente na URL não quebra a página: mostra os valores padrão."""
    detalhe = metricas.montar_detalhe_bloco("Inexistente", [])

    assert detalhe.volume_total == "R$ 0,00"
    assert detalhe.score_medio == "N/A"
    assert detalhe.empresas == []


# -----------------------------------------------------------------------------
# PROJEÇÕES SIMULADAS
# -----------------------------------------------------------------------------
