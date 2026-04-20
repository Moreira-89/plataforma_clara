"""Bootstrap da aplicação Reflex da Plataforma Clara.

Este módulo centraliza o registro de rotas explícitas e garante a importação das
páginas decoradas com ``@rx.page`` (dashboards) para que sejam descobertas pelo
runtime do Reflex.
"""

import reflex as rx

from plataforma_clara.pages.pg_cadastro_usuario import formulario_cadastro
from plataforma_clara.pages.pg_detalhes_bloco import pg_detalhes_bloco
from plataforma_clara.pages.pg_explorar_blocos import explorar_blocos
from plataforma_clara.pages.pg_home import home_page
from plataforma_clara.pages.pg_ingestao_dados import ingestao_dados
from plataforma_clara.pages.pg_login import formulario_login
from plataforma_clara.pages.pg_relatorios import pg_relatorios
from plataforma_clara.states.dashboard_state import DashboardState
from plataforma_clara.states.detalhes_bloco_state import DetalhesBlocoState

# Importações de efeitos colaterais: páginas com @rx.page são registradas ao importar.
import plataforma_clara.pages.pg_dashboard_gestora  # noqa: F401
import plataforma_clara.pages.pg_dashboard_investidor  # noqa: F401

APP_TITULO_BASE = "Plataforma Clara"

app = rx.App()


def _registrar_paginas() -> None:
    """Registra as páginas declaradas via ``app.add_page``."""
    app.add_page(home_page, route="/", title=f"{APP_TITULO_BASE} - Home")
    app.add_page(formulario_login, route="/login-usuario", title="Login")
    app.add_page(formulario_cadastro, route="/cadastro", title="Cadastro de Usuário")
    app.add_page(ingestao_dados, route="/ingestao-dados", title="Ingestão de Dados")
    app.add_page(
        explorar_blocos,
        route="/explorar-blocos",
        title="Explorar Blocos",
        on_load=DashboardState.carregar_dados_gestora,
    )
    app.add_page(pg_relatorios, route="/relatorios", title="Relatórios")
    app.add_page(
        pg_detalhes_bloco,
        route="/detalhes-bloco/[bloco_id]",
        title="Detalhes do Bloco",
        on_load=DetalhesBlocoState.carregar_detalhes,
    )


_registrar_paginas()
