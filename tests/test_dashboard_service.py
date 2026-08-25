"""
Testes de caracterização das consultas e do cache do dashboard.

Cobre `services/dashboard_service`, que hoje mistura três responsabilidades:
consulta SQL, cache em memória e formatação de apresentação. A migração para
FastAPI vai separar essas camadas — estes testes travam o comportamento observável
para que a separação não mude resultados sem querer.

COMO FUNCIONA:
    1. Substituição do banco — `rx.session` é trocado por uma SessaoFake que devolve
       linhas fixas e conta quantas vezes foi consultada.
    2. Verificação de cache — o mesmo serviço é chamado duas vezes; a contagem de
       chamadas ao banco revela se o cache funcionou.
    3. Verificação de falha — uma sessão que levanta exceção comprova que o serviço
       engole o erro e devolve lista vazia.
"""

from __future__ import annotations

import pytest

reflex = pytest.importorskip("reflex", reason="requer o stack completo do Reflex instalado")

from plataforma_clara.services import dashboard_service  # noqa: E402

_CPF = "12345678901"

_LINHAS_BLOCO = [
    {
        "bloco_liquidez_setorial": "Safira",
        "total_alocado": 5000.0,
        "score_medio_reputacao": 82.5,
        "quantidade_aportes": 3,
    }
]


# -----------------------------------------------------------------------------
# CONSULTA DO INVESTIDOR
# -----------------------------------------------------------------------------


def test_metricas_do_investidor_convertem_linhas_em_dicts(monkeypatch, fabricar_sessao_fake):
    """As linhas do SQLAlchemy viram dicts simples, prontos para o estado do Reflex."""
    monkeypatch.setattr(dashboard_service.rx, "session", fabricar_sessao_fake(_LINHAS_BLOCO))

    resultado = dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)

    assert resultado == _LINHAS_BLOCO


def test_consulta_do_investidor_filtra_pelo_documento(monkeypatch, fabricar_sessao_fake):
    """
    O CPF precisa chegar como PARÂMETRO de bind, nunca concatenado na string SQL.
    Este teste é a defesa contra alguém "simplificar" a query para um f-string.
    """
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)
    monkeypatch.setattr(dashboard_service.rx, "session", fabrica)

    dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)

    _query, params = fabrica().chamadas[0]
    assert params == {"cpf_investidor": _CPF}


def test_segunda_chamada_usa_cache_e_nao_toca_o_banco(monkeypatch, fabricar_sessao_fake):
    """Cache com TTL de 5 min: a segunda chamada no mesmo intervalo não consulta o banco."""
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)
    monkeypatch.setattr(dashboard_service.rx, "session", fabrica)

    dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)
    dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)

    assert len(fabrica().chamadas) == 1


def test_force_refresh_ignora_o_cache(monkeypatch, fabricar_sessao_fake):
    """`force_refresh=True` é o escape para quando a gestora acabou de subir um CSV."""
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)
    monkeypatch.setattr(dashboard_service.rx, "session", fabrica)

    dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)
    dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF, force_refresh=True)

    assert len(fabrica().chamadas) == 2


def test_cache_expira_apos_o_ttl(monkeypatch, fabricar_sessao_fake):
    """
    Passado o TTL, o banco é consultado de novo. O relógio é `time.monotonic`, então
    avançamos o tempo em vez de esperar 5 minutos de verdade.
    """
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)
    monkeypatch.setattr(dashboard_service.rx, "session", fabrica)

    relogio = [1000.0]
    monkeypatch.setattr(dashboard_service.time, "monotonic", lambda: relogio[0])

    dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)
    relogio[0] += dashboard_service._CACHE_TTL_SEGUNDOS + 1
    dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)

    assert len(fabrica().chamadas) == 2


def test_cache_e_isolado_por_investidor(monkeypatch, fabricar_sessao_fake):
    """
    Vazamento de dados entre investidores seria grave: o cache é indexado por CPF,
    então um segundo investidor NÃO pode receber os dados cacheados do primeiro.
    """
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)
    monkeypatch.setattr(dashboard_service.rx, "session", fabrica)

    dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)
    dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor="99999999999")

    assert len(fabrica().chamadas) == 2


# -----------------------------------------------------------------------------
# TRATAMENTO DE FALHA
# -----------------------------------------------------------------------------


def test_falha_de_banco_devolve_lista_vazia(monkeypatch, fabricar_sessao_fake):
    """
    CARACTERIZAÇÃO DE COMPORTAMENTO DISCUTÍVEL: o serviço engole a exceção e devolve
    lista vazia. Para o investidor, banco fora do ar é indistinguível de "não há
    aportes" — a tela mostra zeros em vez de um aviso de erro.

    Na migração para FastAPI isso deve virar um erro HTTP explícito (5xx). Quando
    isso acontecer, este teste vai quebrar de propósito.
    """
    fabrica = fabricar_sessao_fake(erro=RuntimeError("conexão recusada"))
    monkeypatch.setattr(dashboard_service.rx, "session", fabrica)

    resultado = dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)

    assert resultado == []


def test_falha_de_banco_nao_envenena_o_cache(monkeypatch, fabricar_sessao_fake):
    """Uma falha não pode gravar `[]` no cache e mascarar os dados por 5 minutos."""
    monkeypatch.setattr(
        dashboard_service.rx, "session", fabricar_sessao_fake(erro=RuntimeError("timeout"))
    )
    dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)

    fabrica_ok = fabricar_sessao_fake(_LINHAS_BLOCO)
    monkeypatch.setattr(dashboard_service.rx, "session", fabrica_ok)
    resultado = dashboard_service.buscar_metricas_blocos_liquidez(cpf_investidor=_CPF)

    assert resultado == _LINHAS_BLOCO


# -----------------------------------------------------------------------------
# FORMATAÇÃO DA TABELA DA GESTORA
# -----------------------------------------------------------------------------


def test_tabela_da_gestora_formata_cnpj_e_moeda(monkeypatch, fabricar_sessao_fake):
    """
    A formatação brasileira (máscara de CNPJ e R$ 1.234,56) acontece no serviço, não
    na UI. Ao migrar para uma API JSON isso deve virar responsabilidade do frontend.
    """
    linhas = [
        {
            "empresa_sacada_nome": "Empresa Sacada LTDA",
            "cnpj_sacado_limpo": "12345678000199",
            "valor_total_alocado": 1234567.89,
            "classificacao_risco": "Baixo",
            "status_atual": "Adimplente",
        }
    ]
    monkeypatch.setattr(dashboard_service.rx, "session", fabricar_sessao_fake(linhas))

    resultado = dashboard_service.buscar_tabela_aportes_gestora()

    assert resultado[0]["cnpj"] == "12.345.678/0001-99"
    assert resultado[0]["valor"] == "R$ 1.234.567,89"


def test_cnpj_curto_recebe_zeros_a_esquerda(monkeypatch, fabricar_sessao_fake):
    """`zfill(14)` reconstrói CNPJs que perderam zeros à esquerda em algum ponto do caminho."""
    linhas = [
        {
            "empresa_sacada_nome": "Empresa X",
            "cnpj_sacado_limpo": "123456000199",
            "valor_total_alocado": 100.0,
            "classificacao_risco": "Alto",
            "status_atual": "Inadimplente",
        }
    ]
    monkeypatch.setattr(dashboard_service.rx, "session", fabricar_sessao_fake(linhas))

    resultado = dashboard_service.buscar_tabela_aportes_gestora()

    assert resultado[0]["cnpj"] == "00.123.456/0001-99"
