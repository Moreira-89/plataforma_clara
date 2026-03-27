import reflex as rx
import pandas as pd


class Usuario(rx.Model):
    tipo_usuario: str  # Esperado: "gestora" ou "investidor"
    nome: str
    email: str
    senha_hash: str