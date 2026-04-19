from plataforma_clara.pages.pg_cadastro_usuario import formulario_cadastro_gestora, formulario_cadastro_investidor
from plataforma_clara.pages.pg_ingestao_dados import ingestao_dados
from plataforma_clara.pages.pg_login import formulario_login
from plataforma_clara.pages.pg_home import home_page
from plataforma_clara.pages.pg_dashboard_gestora import dashboard_gestora
from plataforma_clara.pages.pg_dashboard_investidor import dashboard_investidor

import reflex as rx


app = rx.App()
app.add_page(home_page, route="/", title="Plataforma Clara - Home")
app.add_page(formulario_login, route="/login-usuario", title="Login")
app.add_page(formulario_cadastro_gestora, route="/cadastro-gestora", title="Cadastro de Gestora")
app.add_page(formulario_cadastro_investidor, route="/cadastro-investidor", title="Cadastro de Investidor")
app.add_page(ingestao_dados, route="/ingestao-dados", title="Ingestão de Dados")

