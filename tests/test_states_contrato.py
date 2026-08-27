"""
Testes de contrato entre os states e as páginas.

As páginas do Reflex referenciam vars e event handlers pelo nome
(`DashboardState.patrimonio_total_investidor`, `AutenticacaoState.fazer_login`).
Um nome que some numa refatoração não quebra em tempo de import: quebra na
compilação do frontend ou, pior, silenciosamente na tela.

A Fase 1 mexeu em todos os states, e a suíte não tem como subir o Reflex inteiro
para conferir. Estes testes são a rede de segurança possível: garantem que a
superfície que as páginas consomem continua existindo, com a mesma grafia.

A lista abaixo foi levantada varrendo `pages/` e `components/`. Ao adicionar uma
referência nova numa página, acrescente-a aqui também.
"""

from __future__ import annotations

import pytest

pytest.importorskip("reflex", reason="requer o stack completo do Reflex instalado")

from plataforma_clara.states.assistente_ia_state import AssistenteIAState  # noqa: E402
from plataforma_clara.states.autenticacao_state import AutenticacaoState  # noqa: E402
from plataforma_clara.states.cadastro_usuario_state import CadastroUsuarioState  # noqa: E402
from plataforma_clara.states.dashboard_state import DashboardState  # noqa: E402
from plataforma_clara.states.detalhes_bloco_state import DetalhesBlocoState  # noqa: E402
from plataforma_clara.states.explorar_blocos_state import ExplorarBlocosState  # noqa: E402
from plataforma_clara.states.ingestao_dados_state import IngestaoDadosState  # noqa: E402

# O que cada página lê do state: (classe, vars, event handlers).
_CONTRATOS = [
    (
        DashboardState,
        {
            "alocacao_blocos_investidor",
            "classificacao_risco_medio",
            "dados_blocos",
            "dados_distribuicao_aportes",
            "dados_evolucao_aum",
            "dados_grafico_pizza",
            "dados_rendimento_projetado",
            "inadimplencia_projetada",
            "patrimonio_total_gestora_formatado",
            "patrimonio_total_investidor",
            "qtd_blocos_ativos",
            "quantidade_total_aportes",
            "score_medio_geral",
            "tabela_aportes_gestora",
            "tabela_transparencia_investidor",
        },
        {"carregar_dados_dashboard", "carregar_dados_gestora"},
    ),
    (
        AutenticacaoState,
        {"mensagem_para_usuario"},
        {"fazer_login", "fazer_logout", "set_email_usuario", "set_senha_hash_usuario"},
    ),
    (
        CadastroUsuarioState,
        {"mensagem_para_usuario", "tipo_usuario"},
        {
            "identificar_tipo_usuario",
            "set_email_usuario",
            "set_identificador_usuario",
            "set_nome_usuario",
            "set_senha_hash_usuario",
            "set_tipo_usuario",
        },
    ),
    (
        ExplorarBlocosState,
        {"blocos_filtrados"},
        {"set_filtro_score", "set_filtro_setor", "set_termo_busca"},
    ),
    (
        DetalhesBlocoState,
        {
            "empresas_bloco",
            "nome_bloco",
            "prazo_medio",
            "rentabilidade_alvo",
            "score_medio",
            "volume_total",
        },
        {"carregar_detalhes"},
    ),
    (
        IngestaoDadosState,
        {"mensagem_para_usuario"},
        {"lidar_com_upload_de_arquivo"},
    ),
    (
        AssistenteIAState,
        {"is_loading", "mensagem_para_usuario", "opcoes_relatorio", "relatorio_selecionado"},
        {"gerar_e_baixar_relatorio", "set_relatorio_selecionado"},
    ),
]


@pytest.mark.parametrize(
    ("estado", "vars_esperadas", "handlers_esperados"),
    _CONTRATOS,
    ids=lambda valor: valor.__name__ if hasattr(valor, "__name__") else "",
)
def test_state_expoe_o_que_as_paginas_consomem(estado, vars_esperadas, handlers_esperados):
    """Toda var e todo handler citado nas páginas precisa existir no state."""
    assert vars_esperadas <= set(estado.vars)
    assert handlers_esperados <= set(estado.event_handlers)


def test_states_de_bloco_herdam_os_dados_do_dashboard():
    """
    A herança não é decorativa: `ExplorarBlocosState` filtra `dados_blocos_gestora`,
    que quem carrega é o `DashboardState`. Trocar a herança por composição exige
    resolver de onde os dados vêm.
    """
    assert issubclass(ExplorarBlocosState, DashboardState)
    assert issubclass(DetalhesBlocoState, DashboardState)
    assert "dados_blocos_gestora" in ExplorarBlocosState.vars
