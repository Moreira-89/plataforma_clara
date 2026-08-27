"""
Testes das regras de risco e da formatação brasileira.

Cobre `domain/risco.py` e `domain/formatacao.py` — as duas maiores fontes de
duplicação antes da Fase 1. A escada de risco existia em quatro lugares (um deles
dentro de um `CASE WHEN` de SQL) e a formatação de moeda em quatro outros.

Os valores esperados aqui vieram do código anterior à extração, não de uma
especificação: se um deles mudar, a pergunta é se a mudança foi intencional.

Nenhum destes testes precisa de banco, de rede ou do Reflex.
"""

from __future__ import annotations

import pytest

from plataforma_clara.domain import formatacao, risco

# -----------------------------------------------------------------------------
# ESCADA DE RISCO
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "nota"),
    [
        (100.0, "A+"),
        (80.0, "A+"),
        (79.9, "A"),
        (70.0, "A"),
        (60.0, "A-"),
        (50.0, "B+"),
        (40.0, "B"),
        (39.9, "C-"),
        (0.0, "C-"),
    ],
)
def test_nota_de_credito_respeita_os_pisos(score, nota):
    """Os limites das faixas são inclusivos no piso — 80 é A+, 79.9 já é A."""
    assert risco.classificar_nota(score) == nota


@pytest.mark.parametrize(
    ("score", "esperado"),
    [
        (85.0, "A+ (Baixo Risco)"),
        (65.0, "A- (Baixo Risco)"),
        (45.0, "B (Médio Risco)"),
        (10.0, "C- (Alto Risco)"),
    ],
)
def test_formato_da_pagina_de_detalhes(score, esperado):
    """Formato 'nota (nível Risco)', usado no cabeçalho do bloco."""
    assert risco.classificar_nota_com_nivel(score) == esperado


@pytest.mark.parametrize(
    ("score", "esperado"),
    [
        (85.0, "Baixo (A+)"),
        (75.0, "Baixo (A)"),
        (65.0, "Moderado (A-)"),
        (55.0, "Médio (B+)"),
        (45.0, "Alto (B)"),
        (10.0, "Crítico (C-)"),
    ],
)
def test_formato_do_kpi_do_dashboard(score, esperado):
    """
    CARACTERIZAÇÃO DE INCONSISTÊNCIA CONHECIDA: o vocabulário de nível aqui NÃO é o
    mesmo da página de detalhes. Um score de 45 é 'Médio Risco' no bloco e 'Alto' no
    KPI; 65 é 'Baixo' lá e 'Moderado' aqui. A divergência é anterior à Fase 1 e foi
    preservada de propósito — unificar é decisão de produto.
    """
    assert risco.classificar_nivel_com_nota(score) == esperado


def test_score_zerado_no_kpi_vira_na_em_vez_de_critico():
    """Sem dados, a plataforma não afirma que o risco é crítico — mostra 'N/A'."""
    assert risco.classificar_nivel_com_nota(0.0) == "N/A"


@pytest.mark.parametrize(
    ("score", "status"),
    [
        (85.0, "Adimplente"),
        (60.0, "Adimplente"),
        (59.9, "Atenção"),
        (40.0, "Atenção"),
        (39.9, "Inadimplente"),
    ],
)
def test_status_de_adimplencia(score, status):
    """Faixas que antes vinham do segundo `CASE WHEN` da query da gestora."""
    assert risco.classificar_adimplencia(score) == status


def test_corte_de_inadimplencia_projetada_e_mais_conservador_que_atencao():
    """O KPI da gestora usa 50 como corte, não os 40 do status 'Atenção'."""
    assert risco.esta_em_risco_de_inadimplencia(49.9)
    assert not risco.esta_em_risco_de_inadimplencia(50.0)


# -----------------------------------------------------------------------------
# FORMATAÇÃO
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (1234567.89, "R$ 1.234.567,89"),
        (0.0, "R$ 0,00"),
        (1000.5, "R$ 1.000,50"),
        (-42.0, "R$ -42,00"),
    ],
)
def test_moeda_no_padrao_brasileiro(valor, esperado):
    """Ponto de milhar, vírgula decimal — o que o investidor brasileiro espera ler."""
    assert formatacao.formatar_moeda(valor) == esperado


@pytest.mark.parametrize(
    ("cnpj", "esperado"),
    [
        ("12345678000199", "12.345.678/0001-99"),
        ("123456000199", "00.123.456/0001-99"),
    ],
)
def test_mascara_de_cnpj(cnpj, esperado):
    """Zeros à esquerda são reconstruídos antes de aplicar a máscara."""
    assert formatacao.formatar_cnpj(cnpj) == esperado


def test_valor_que_nao_e_cnpj_sai_preenchido_com_zeros_e_sem_mascara():
    """
    CARACTERIZAÇÃO DE COMPORTAMENTO ESQUISITO: o `zfill(14)` roda ANTES da checagem
    de validade, então lixo curto volta com zeros grudados na frente ('0000não é
    cnpj') em vez de intacto. Não chega a aparecer na tela — o CNPJ vem sempre de
    coluna normalizada —, mas a função não é segura para entrada arbitrária.
    """
    assert formatacao.formatar_cnpj("não é cnpj") == "0000não é cnpj"


def test_valor_em_milhoes_abaixo_de_um_bilhao():
    """O caso normal dos cards de Explorar Blocos."""
    assert formatacao.formatar_milhoes(12_300_000.0) == "R$ 12,3M"


def test_valor_em_milhoes_acima_de_um_bilhao_sai_errado():
    """
    CARACTERIZAÇÃO DE BUG: a troca de símbolos é parcial e o separador de milhar do
    Python sobrevive, produzindo 'R$ 1,500,0M' para R$ 1,5 bilhão. O comportamento é
    o atual da tela e foi preservado; corrigir é mudança de UI, prevista para a Fase 5.
    """
    assert formatacao.formatar_milhoes(1_500_000_000.0) == "R$ 1,500,0M"


@pytest.mark.parametrize(
    ("entrada", "esperado"), [(None, 0.0), ("", 0.0), ("abc", 0.0), ("12.5", 12.5)]
)
def test_conversao_tolerante_para_float(entrada, esperado):
    """Agregações SQL devolvem None e Decimal; nada disso pode derrubar a tela."""
    assert formatacao.para_float(entrada) == esperado
