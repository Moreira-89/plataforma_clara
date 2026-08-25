"""
Testes de caracterização da preparação de dados do relatório por IA.

Cobre as funções puras de `services/relatorio_ia_service` — normalização,
agregação e compactação do payload. A chamada ao Groq e a geração do PDF NÃO são
exercitadas aqui: dependem de rede e de API key, e o roadmap prevê que virem nós
de um grafo LangGraph na Fase 4.

O que importa travar antes da migração é a MATEMÁTICA da compactação: é ela que
decide o que o LLM vê. Se a agregação mudar em silêncio, o relatório entregue ao
investidor muda de conteúdo sem que nada quebre visivelmente.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("groq", reason="requer o stack completo (groq/langchain) instalado")

from plataforma_clara.services import relatorio_ia_service as servico  # noqa: E402

# -----------------------------------------------------------------------------
# NORMALIZAÇÃO
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("123.456.789-01", "12345678901"),
        ("12.345.678/0001-99", "12345678000199"),
        ("12345678901", "12345678901"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalizacao_de_documento(entrada, esperado):
    """
    O documento é normalizado em 3 lugares (login, CSV, relatório) e todos precisam
    concordar — senão o investidor recebe um relatório vazio apesar de ter aportes.
    """
    assert servico._normalizar_documento(entrada) == esperado


def test_estimativa_de_tokens_ignora_textos_vazios():
    """A heurística de ~3.6 chars por token é o que decide se o payload é reduzido."""
    assert servico._estimar_tokens_aprox("") == 0
    assert servico._estimar_tokens_aprox("a" * 36) == 10
    assert servico._estimar_tokens_aprox("a" * 18, "", "a" * 18) == 10


def test_json_compacto_preserva_acentos():
    """
    `ensure_ascii=False` é deliberado: nomes de empresas brasileiras têm acento, e
    escapar tudo para \\uXXXX inflaria o payload justamente no que é caro (tokens).
    """
    resultado = servico._to_json_compacto({"empresa": "Ação Comércio"})

    assert "Ação Comércio" in resultado
    assert json.loads(resultado)["empresa"] == "Ação Comércio"


# -----------------------------------------------------------------------------
# COMPACTAÇÃO DO PAYLOAD
# -----------------------------------------------------------------------------


def _aporte(bloco: str, empresa: str, valor: float, score: float) -> dict:
    return {
        "bloco_liquidez_setorial": bloco,
        "empresa_sacada_nome": empresa,
        "valor_aporte_compra": valor,
        "score_risco_interno": score,
    }


def test_compactacao_agrega_valores_e_media_por_bloco():
    """
    Regra central: o valor por bloco é SOMA e o score é MÉDIA. Trocar um pelo outro
    produziria um relatório plausível e completamente errado.
    """
    dados = [
        _aporte("Safira", "Empresa A", 100.0, 80.0),
        _aporte("Safira", "Empresa B", 300.0, 60.0),
    ]

    dados_bq, _invest, _meta = servico._compactar_dados_para_prompt(
        dados, limite_amostra=10, limite_empresas=10
    )
    bloco = dados_bq["resumo_blocos"][0]

    assert bloco["valor_total_aportado"] == 400.0
    assert bloco["score_medio"] == 70.0


def test_compactacao_preserva_todos_os_blocos():
    """
    O limite corta EMPRESAS, nunca BLOCOS: a visão consolidada por bloco de liquidez
    é o produto principal da plataforma e não pode ser truncada.
    """
    dados = [_aporte(f"Bloco {i}", f"Empresa {i}", 100.0, 50.0) for i in range(30)]

    dados_bq, invest, meta = servico._compactar_dados_para_prompt(
        dados, limite_amostra=5, limite_empresas=5
    )

    assert len(dados_bq["resumo_blocos"]) == 30
    assert meta["qtd_blocos_total"] == 30
    assert len(invest) == 5


def test_compactacao_limita_a_amostra_de_aportes():
    """A amostra crua existe para dar textura ao LLM; é a primeira coisa a ser cortada."""
    dados = [_aporte("Safira", f"Empresa {i}", 100.0, 50.0) for i in range(50)]

    dados_bq, _invest, meta = servico._compactar_dados_para_prompt(
        dados, limite_amostra=8, limite_empresas=100
    )

    assert len(dados_bq["amostra_aportes"]) == 8
    assert meta["qtd_aportes_amostra_enviada"] == 8
    # O total real é preservado no meta para o LLM saber que viu só uma fatia.
    assert meta["qtd_registros_total"] == 50


def test_compactacao_agrupa_por_bloco_e_empresa():
    """A mesma empresa em blocos diferentes são grupos distintos — não podem ser fundidos."""
    dados = [
        _aporte("Safira", "Empresa A", 100.0, 80.0),
        _aporte("Rubi", "Empresa A", 200.0, 40.0),
        _aporte("Safira", "Empresa A", 50.0, 60.0),
    ]

    _dados_bq, invest, _meta = servico._compactar_dados_para_prompt(
        dados, limite_amostra=10, limite_empresas=10
    )

    assert len(invest) == 2
    safira = next(g for g in invest if g["bloco_liquidez_setorial"] == "Safira")
    assert safira["valor_investido"] == 150.0
    assert safira["quantidade_aportes"] == 2


def test_compactacao_tolera_campos_nulos():
    """
    Dados do BigQuery chegam com nulos. A compactação precisa degradar para "N/A" e
    0.0 em vez de estourar — um relatório parcial vale mais que uma exceção na tela.
    """
    dados = [
        {
            "bloco_liquidez_setorial": None,
            "empresa_sacada_nome": None,
            "valor_aporte_compra": None,
            "score_risco_interno": None,
        }
    ]

    dados_bq, invest, _meta = servico._compactar_dados_para_prompt(
        dados, limite_amostra=10, limite_empresas=10
    )

    assert dados_bq["resumo_blocos"][0]["bloco_liquidez_setorial"] == "N/A"
    assert invest[0]["nome_empresa"] == "N/A"
    assert invest[0]["valor_investido"] == 0.0


def test_compactacao_de_lista_vazia_nao_estoura():
    """Investidor sem aportes é barrado antes, mas a função não pode quebrar por isso."""
    dados_bq, invest, meta = servico._compactar_dados_para_prompt(
        [], limite_amostra=10, limite_empresas=10
    )

    assert dados_bq["resumo_blocos"] == []
    assert invest == []
    assert meta["qtd_registros_total"] == 0


# -----------------------------------------------------------------------------
# PDF DE REFERÊNCIA (D9 no roadmap)
# -----------------------------------------------------------------------------


def test_pdf_de_referencia_ausente_degrada_para_string_vazia():
    """
    CARACTERIZAÇÃO DE D9: o PDF de few-shot citado no prompt não existe no repositório.
    O código trata a ausência sem quebrar, mas o relatório é gerado SEM o exemplo que
    o prompt institucional pressupõe. Documentado aqui para que a decisão da Fase 4
    (versionar o arquivo ou remover a dependência) seja consciente.
    """
    assert not servico._PDF_REFERENCIA_PATH.exists()
    assert servico._ler_pdf_referencia() == ""


def test_montagem_de_investimentos_usa_defaults_para_campos_ausentes():
    """O payload enviado ao LLM tem forma fixa, mesmo com linhas incompletas do BigQuery."""
    resultado = servico._montar_dados_investimentos("Fulano", [{}])

    assert resultado == [
        {
            "nome_investidor": "Fulano",
            "nome_empresa": "N/A",
            "score_ml": 0.0,
            "valor_investido": 0.0,
        }
    ]
