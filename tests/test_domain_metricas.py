"""
Testes das regras de negócio dos dashboards.

Cobre `domain/metricas.py` e `domain/projecoes.py` — o que antes vivia dentro de
computed vars e métodos privados de `rx.State`, inalcançável sem subir o Reflex.

O que estes testes travam é a MATEMÁTICA que o investidor vê: consolidação de KPIs,
peso de cada empresa no bloco e as faixas dos filtros. Um erro aqui produz uma tela
plausível e errada, que é o pior tipo de erro num produto de transparência.
"""

from __future__ import annotations

import pytest

from plataforma_clara.domain import metricas, projecoes
from plataforma_clara.domain.schemas import AgregadoEmpresa, MetricaBloco


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


def test_percentual_de_blocos_em_risco():
    """Um de quatro blocos abaixo de 50 dá 25%."""
    blocos = [
        _bloco("A", 1.0, 80.0),
        _bloco("B", 1.0, 70.0),
        _bloco("C", 1.0, 60.0),
        _bloco("D", 1.0, 30.0),
    ]

    assert metricas.percentual_blocos_em_risco(blocos) == "25.0%"


def test_percentual_sem_blocos_e_zero():
    assert metricas.percentual_blocos_em_risco([]) == "0.0%"


@pytest.mark.parametrize(
    ("quantidade", "esperado"), [(0, "0 Blocos"), (1, "1 Bloco"), (2, "2 Blocos")]
)
def test_concordancia_de_numero_na_contagem_de_blocos(quantidade, esperado):
    blocos = [_bloco(f"B{i}", 1.0, 50.0) for i in range(quantidade)]

    assert metricas.descrever_quantidade_blocos(blocos) == esperado


def test_series_de_grafico_convertem_para_milhoes():
    """Os gráficos plotam em milhões para caber no eixo."""
    serie = metricas.serie_alocacao_por_bloco([_bloco("Safira", 12_345_678.0, 80.0)])

    assert serie == [{"name": "Safira", "value": 12.35}]


def test_distribuicao_mostra_apenas_os_cinco_maiores():
    """A lista chega ordenada do banco; o corte é de apresentação."""
    blocos = [_bloco(f"B{i}", 100.0 * i, 50.0) for i in range(10)]

    assert len(metricas.serie_distribuicao_aportes(blocos)) == 5


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


def test_sem_filtros_todos_os_blocos_viram_cards():
    cards = metricas.filtrar_blocos([_bloco("Safira", 1.0, 80.0), _bloco("Rubi", 1.0, 40.0)])

    assert len(cards) == 2


def test_busca_por_texto_e_case_insensitive():
    cards = metricas.filtrar_blocos(
        [_bloco("Safira", 1.0, 80.0), _bloco("Rubi", 1.0, 80.0)], termo_busca="SAF"
    )

    assert [card.nome for card in cards] == ["Safira"]


def test_busca_com_espaco_sobrando_nao_encontra_nada():
    """
    CARACTERIZAÇÃO DE BUG: o termo é testado com `.strip()` mas comparado sem strip,
    então "safira " (com espaço) não casa com nada. Comportamento anterior à Fase 1,
    preservado; corrigir muda o que o usuário vê digitando.
    """
    assert metricas.filtrar_blocos([_bloco("Safira", 1.0, 80.0)], termo_busca="safira ") == []


@pytest.mark.parametrize(
    ("filtro", "scores_esperados"),
    [
        ("A+ a A-", [85.0, 60.0]),
        ("B+ a B-", [45.0]),
        ("C+ ou menor", [20.0]),
        ("Qualquer Score", [85.0, 60.0, 45.0, 20.0]),
        ("", [85.0, 60.0, 45.0, 20.0]),
    ],
)
def test_faixas_do_filtro_de_score(filtro, scores_esperados):
    """As quatro opções do seletor cobrem a escala inteira, sem sobreposição."""
    blocos = [_bloco(f"B{score}", 1.0, score) for score in (85.0, 60.0, 45.0, 20.0)]

    cards = metricas.filtrar_blocos(blocos, filtro_score=filtro)

    assert [float(card.nome[1:]) for card in cards] == scores_esperados


def test_filtro_de_setor_todos_nao_filtra():
    """'Todos os Setores' é rótulo de UI, não um setor de verdade."""
    cards = metricas.filtrar_blocos([_bloco("Safira", 1.0, 80.0)], filtro_setor="Todos os Setores")

    assert len(cards) == 1


def test_card_codifica_o_nome_para_a_rota_dinamica():
    """Nome com espaço vira `%20` — senão a rota /bloco/[bloco_id] quebra."""
    cards = metricas.filtrar_blocos([_bloco("Bloco Safira", 1.0, 80.0)])

    assert cards[0].id_bloco == "Bloco%20Safira"


def test_rentabilidade_simulada_e_estavel_e_fica_na_faixa():
    """
    O número é inventado (ver o aviso em `rentabilidade_estavel`), mas precisa ser o
    MESMO a cada renderização — senão o card pisca valores diferentes na tela.
    """
    primeira = metricas.rentabilidade_estavel("Safira")

    assert primeira == metricas.rentabilidade_estavel("Safira")
    assert 10.5 <= primeira <= 17.5


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


def test_evolucao_do_aum_termina_no_valor_atual():
    """
    A série é SIMULADA: o último ponto é o patrimônio de hoje e os anteriores são
    frações fixas dele. Nenhum histórico é consultado — ver `domain/projecoes.py`.
    """
    serie = projecoes.evolucao_aum_simulada(100_000_000.0)

    assert len(serie) == 6
    assert serie[-1]["volume"] == 100.0
    assert serie[0]["volume"] == 83.0


def test_rendimento_projetado_comeca_do_zero_e_cresce():
    """O primeiro mês mostra o ganho de 1%, não o total — é rendimento acumulado."""
    serie = projecoes.rendimento_projetado_simulado(100_000_000.0)

    assert serie[0]["rendimento"] == 1.0
    assert serie[-1]["rendimento"] > serie[0]["rendimento"]
