"""
Testes de caracterização das consultas e do cache do dashboard.

Cobre `services/dashboard_service`, que depois da extração do domínio faz três
coisas: decide o escopo da sessão, aplica o cache e traduz falha de banco em
resposta vazia. O SQL está em `infra/repositorios/aporte.py` e a formatação em
`domain/metricas.py` — ambos com testes próprios.

COMO FUNCIONA:
    1. Substituição do banco — a fábrica de sessão falsa entra por parâmetro
       (`sessao_factory=`), sem monkeypatch: é a injeção de dependência da Fase 1.
    2. Verificação de cache — o mesmo serviço é chamado duas vezes e a contagem de
       chamadas ao banco revela se o cache funcionou.
    3. Verificação de falha — uma sessão que levanta exceção comprova que o serviço
       engole o erro e devolve vazio.
"""

from __future__ import annotations

import pytest

pytest.importorskip("sqlmodel", reason="requer o stack de banco instalado")

from plataforma_clara.services import dashboard_service  # noqa: E402

_DOCUMENTO = "12345678901"

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


def test_metricas_do_investidor_viram_dtos(fabricar_sessao_fake):
    """As linhas do banco viram `MetricaBloco` — o contrato que a Fase 2 vai serializar."""
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)

    resultado = dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO, sessao_factory=fabrica
    )

    assert [bloco.model_dump() for bloco in resultado] == _LINHAS_BLOCO


def test_consulta_do_investidor_filtra_por_bind_parameter(fabricar_sessao_fake):
    """
    O documento precisa chegar como PARÂMETRO de bind, nunca concatenado no SQL.
    Este teste é a defesa contra alguém "simplificar" a query para um f-string.
    """
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)

    dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO, sessao_factory=fabrica
    )

    consulta, parametros = fabrica().chamadas[0]
    assert parametros == {"documento": _DOCUMENTO}
    assert _DOCUMENTO not in str(consulta)


def test_visao_da_gestora_nao_filtra_por_investidor(fabricar_sessao_fake):
    """Sem documento, a mesma agregação roda sobre a base inteira e sem parâmetros."""
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)

    dashboard_service.buscar_metricas_gerais_gestora(sessao_factory=fabrica)

    consulta, parametros = fabrica().chamadas[0]
    assert parametros == {}
    assert "documento_investidor_cpf_cnpj" not in str(consulta)


def test_segunda_chamada_usa_cache_e_nao_toca_o_banco(fabricar_sessao_fake):
    """Cache com TTL de 5 min: a segunda chamada no mesmo intervalo não consulta o banco."""
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)

    dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO, sessao_factory=fabrica
    )
    dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO, sessao_factory=fabrica
    )

    assert len(fabrica().chamadas) == 1


def test_force_refresh_ignora_o_cache(fabricar_sessao_fake):
    """`force_refresh=True` é o escape para quando a gestora acabou de subir um CSV."""
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)

    dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO, sessao_factory=fabrica
    )
    dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO, force_refresh=True, sessao_factory=fabrica
    )

    assert len(fabrica().chamadas) == 2


def test_cache_expira_apos_o_ttl(monkeypatch, fabricar_sessao_fake):
    """
    Passado o TTL, o banco é consultado de novo. O relógio é `time.monotonic`, então
    avançamos o tempo em vez de esperar 5 minutos de verdade.
    """
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)

    relogio = [1000.0]
    monkeypatch.setattr(dashboard_service.time, "monotonic", lambda: relogio[0])

    dashboard_service.buscar_metricas_gerais_gestora(sessao_factory=fabrica)
    relogio[0] += dashboard_service._CACHE_TTL_SEGUNDOS + 1
    dashboard_service.buscar_metricas_gerais_gestora(sessao_factory=fabrica)

    assert len(fabrica().chamadas) == 2


def test_cache_e_isolado_por_investidor(fabricar_sessao_fake):
    """
    Vazamento de dados entre investidores seria grave: a chave do cache inclui o
    documento, então um segundo investidor NÃO recebe os dados cacheados do primeiro.
    """
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)

    dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO, sessao_factory=fabrica
    )
    dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor="99999999999", sessao_factory=fabrica
    )

    assert len(fabrica().chamadas) == 2


def test_cache_do_investidor_nao_e_o_cache_da_gestora(fabricar_sessao_fake):
    """
    As duas visões usam a mesma agregação, mas com escopos diferentes. Compartilhar
    a entrada de cache faria a gestora ver a carteira de um investidor só — ou pior,
    o investidor ver a base inteira.
    """
    fabrica = fabricar_sessao_fake(_LINHAS_BLOCO)

    dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO, sessao_factory=fabrica
    )
    dashboard_service.buscar_metricas_gerais_gestora(sessao_factory=fabrica)

    assert len(fabrica().chamadas) == 2


# -----------------------------------------------------------------------------
# TRATAMENTO DE FALHA
# -----------------------------------------------------------------------------


def test_falha_de_banco_devolve_lista_vazia(fabricar_sessao_fake):
    """
    CARACTERIZAÇÃO DE COMPORTAMENTO DISCUTÍVEL: o serviço engole a exceção e devolve
    lista vazia. Para o investidor, banco fora do ar é indistinguível de "não há
    aportes" — a tela mostra zeros em vez de um aviso de erro.

    Na Fase 2 isso deve virar um erro HTTP explícito (5xx). Quando isso acontecer,
    este teste vai quebrar de propósito.
    """
    fabrica = fabricar_sessao_fake(erro=RuntimeError("conexão recusada"))

    resultado = dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO, sessao_factory=fabrica
    )

    assert resultado == []


def test_falha_de_banco_nao_envenena_o_cache(fabricar_sessao_fake):
    """Uma falha não pode gravar `[]` no cache e mascarar os dados por 5 minutos."""
    dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO,
        sessao_factory=fabricar_sessao_fake(erro=RuntimeError("timeout")),
    )

    resultado = dashboard_service.buscar_metricas_blocos_liquidez(
        documento_investidor=_DOCUMENTO,
        sessao_factory=fabricar_sessao_fake(_LINHAS_BLOCO),
    )

    assert [bloco.model_dump() for bloco in resultado] == _LINHAS_BLOCO


def test_falha_no_patrimonio_total_devolve_zero(fabricar_sessao_fake):
    """Patrimônio é um número só — a falha degrada para zero, não para None."""
    fabrica = fabricar_sessao_fake(erro=RuntimeError("sem conexão"))

    assert dashboard_service.buscar_patrimonio_total(sessao_factory=fabrica) == 0.0


# -----------------------------------------------------------------------------
# TABELA DA GESTORA
# -----------------------------------------------------------------------------


def test_tabela_da_gestora_formata_cnpj_e_moeda(fabricar_sessao_fake):
    """
    A formatação brasileira acontece no domínio, não na UI nem no SQL. Ao migrar
    para uma API JSON isso deve virar responsabilidade do frontend (Fase 5).
    """
    linhas = [
        {
            "empresa_sacada_nome": "Empresa Sacada LTDA",
            "cnpj_sacado_limpo": "12345678000199",
            "valor_total_alocado": 1234567.89,
            "score_medio": 85.0,
        }
    ]

    resultado = dashboard_service.buscar_tabela_aportes_gestora(
        sessao_factory=fabricar_sessao_fake(linhas)
    )

    assert resultado[0].cnpj == "12.345.678/0001-99"
    assert resultado[0].valor == "R$ 1.234.567,89"


def test_classificacao_de_risco_saiu_do_sql_e_continua_igual(fabricar_sessao_fake):
    """
    REGRESSÃO DA FASE 1: a nota e o status vinham de um `CASE WHEN` na query e agora
    são calculados em `domain/risco.py`. As faixas precisam continuar as mesmas —
    um score de 85 é 'A+' e 'Adimplente' antes e depois da mudança.
    """
    linhas = [
        {
            "empresa_sacada_nome": "Empresa X",
            "cnpj_sacado_limpo": "12345678000199",
            "valor_total_alocado": 100.0,
            "score_medio": 85.0,
        }
    ]

    resultado = dashboard_service.buscar_tabela_aportes_gestora(
        sessao_factory=fabricar_sessao_fake(linhas)
    )

    assert resultado[0].risco == "A+"
    assert resultado[0].status == "Adimplente"


def test_cnpj_curto_recebe_zeros_a_esquerda(fabricar_sessao_fake):
    """`zfill(14)` reconstrói CNPJs que perderam zeros à esquerda em algum ponto do caminho."""
    linhas = [
        {
            "empresa_sacada_nome": "Empresa X",
            "cnpj_sacado_limpo": "123456000199",
            "valor_total_alocado": 100.0,
            "score_medio": 30.0,
        }
    ]

    resultado = dashboard_service.buscar_tabela_aportes_gestora(
        sessao_factory=fabricar_sessao_fake(linhas)
    )

    assert resultado[0].cnpj == "00.123.456/0001-99"


# -----------------------------------------------------------------------------
# TABELA DE TRANSPARÊNCIA
# -----------------------------------------------------------------------------


class _LinhaOrm:
    """Imita a linha nomeada que o Query do SQLAlchemy devolve."""

    def __init__(self, empresa: str, bloco: str | None, score: float, valor: float):
        self.empresa_sacada_nome = empresa
        self.bloco_liquidez_setorial = bloco
        self.score_medio = score
        self.valor_total = valor


def test_transparencia_formata_valor_e_arredonda_score(fabricar_sessao_fake):
    """A tabela que dá nome à plataforma: em quais empresas o dinheiro foi aplicado."""
    fabrica = fabricar_sessao_fake(objetos=[_LinhaOrm("Empresa A", "Safira", 78.456, 1234.5)])

    resultado = dashboard_service.buscar_tabela_transparencia_investidor(
        documento_investidor=_DOCUMENTO, sessao_factory=fabrica
    )

    assert resultado[0].valor == "R$ 1.234,50"
    assert resultado[0].score == 78.46


def test_transparencia_sem_bloco_mostra_na(fabricar_sessao_fake):
    """Aporte sem bloco não some da tabela — aparece como 'N/A'."""
    fabrica = fabricar_sessao_fake(objetos=[_LinhaOrm("Empresa A", None, 50.0, 100.0)])

    resultado = dashboard_service.buscar_tabela_transparencia_investidor(
        documento_investidor=_DOCUMENTO, sessao_factory=fabrica
    )

    assert resultado[0].bloco == "N/A"
