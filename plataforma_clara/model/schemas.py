import reflex as rx
import pandas as pd


class tb_usuario(rx.Model, table=True):
    tipo_usuario: str  # Esperado: "gestora" ou "investidor"
    nome: str
    email: str
    senha_hash: str