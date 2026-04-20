from plataforma_clara.pages.pg_cadastro_usuario import formulario_cadastro
from plataforma_clara.pages.pg_ingestao_dados import ingestao_dados
from plataforma_clara.pages.pg_login import formulario_login
from plataforma_clara.pages.pg_home import home_page
from plataforma_clara.pages.pg_explorar_blocos import explorar_blocos
from plataforma_clara.pages.pg_relatorios import pg_relatorios
from plataforma_clara.pages.pg_detalhes_bloco import pg_detalhes_bloco
# Dashboards usam @rx.page() — importar o módulo é suficiente para registrar
import plataforma_clara.pages.pg_dashboard_gestora  # noqa: F401
import plataforma_clara.pages.pg_dashboard_investidor  # noqa: F401

import reflex as rx

app = rx.App()
app.add_page(home_page, route="/", title="Plataforma Clara - Home")
app.add_page(formulario_login, route="/login-usuario", title="Login")
app.add_page(formulario_cadastro, route="/cadastro", title="Cadastro de Usuário")
app.add_page(ingestao_dados, route="/ingestao-dados", title="Ingestão de Dados")
app.add_page(explorar_blocos, route="/explorar-blocos", title="Explorar Blocos")
app.add_page(pg_relatorios, route="/relatorios", title="Relatórios")
app.add_page(pg_detalhes_bloco, route="/detalhes-bloco", title="Detalhes do Bloco")