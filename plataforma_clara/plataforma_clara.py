"""
Bootstrap e registro de rotas da aplicação Reflex — Plataforma Clara.

Este módulo é o ponto de entrada do servidor Reflex. Centraliza:
    1. Instanciação do app (`rx.App`).
    2. Importação de páginas com @rx.page (efeito colateral necessário para o Reflex descobrí-las).
    3. Registro explícito de rotas via `app.add_page` para páginas sem @rx.page.

COMO FUNCIONA:
    O Reflex utiliza dois mecanismos de registro de páginas:
        - @rx.page: decorador que registra a página automaticamente ao importar o módulo.
        - app.add_page(): registro manual, necessário para páginas com parâmetros de rota
          dinâmicos (ex: [bloco_id]) ou com `on_load` (hook de carregamento de dados).
    Ambos os mecanismos são combinados aqui para cobrir todos os casos.
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

# Importações de efeito colateral: o decorador @rx.page registra a página no Reflex
# assim que o módulo é importado. O # noqa: F401 suprime o aviso de "import não usado",
# pois o import é intencional (efeito colateral), não para usar um símbolo.
import plataforma_clara.pages.pg_dashboard_gestora  # noqa: F401
import plataforma_clara.pages.pg_dashboard_investidor  # noqa: F401

# -----------------------------------------------------------------------------
# INSTANCIAÇÃO DO APP
# -----------------------------------------------------------------------------

APP_TITULO_BASE = "Plataforma Clara"

app = rx.App()


# -----------------------------------------------------------------------------
# REGISTRO DE ROTAS
# -----------------------------------------------------------------------------


def _registrar_paginas() -> None:
    """
    Registra todas as páginas da aplicação via app.add_page.

    COMO FUNCIONA:
        Cada chamada define a rota (URL), o título da aba e, quando aplicável,
        o hook on_load (evento disparado ao navegar para a página — equivalente
        ao useEffect de montagem no React).

    Páginas com @rx.page (gestora e investidor) são registradas automaticamente
    pelos imports de efeito colateral acima e não precisam de app.add_page.
    """
    # Landing page — sem on_load (conteúdo estático)
    app.add_page(home_page, route="/", title=f"{APP_TITULO_BASE} - Home")

    # Autenticação
    app.add_page(formulario_login, route="/login-usuario", title="Login")
    app.add_page(formulario_cadastro, route="/cadastro", title="Cadastro de Usuário")

    # Portal da Gestora
    app.add_page(ingestao_dados, route="/ingestao-dados", title="Ingestão de Dados")

    # Portal do Investidor
    app.add_page(
        explorar_blocos,
        route="/explorar-blocos",
        title="Explorar Blocos",
        # on_load garante que os dados da gestora (lista de blocos) sejam carregados
        # antes de renderizar os cards, evitando estado vazio na primeira carga.
        on_load=DashboardState.carregar_dados_gestora,
    )
    app.add_page(pg_relatorios, route="/relatorios", title="Relatórios")
    app.add_page(
        pg_detalhes_bloco,
        route="/detalhes-bloco/[bloco_id]",
        title="Detalhes do Bloco",
        # DetalhesBlocoState.carregar_detalhes lê o parâmetro [bloco_id] da URL
        # e dispara a query ao banco ao montar a página.
        on_load=DetalhesBlocoState.carregar_detalhes,
    )


_registrar_paginas()
