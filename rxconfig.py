import reflex as rx
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para a memória do sistema
load_dotenv()

config = rx.Config(
    app_name="plataforma_clara",
    db_url=os.getenv("DATABASE_URL"),
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
    
)