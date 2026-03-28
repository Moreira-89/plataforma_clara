import reflex as rx


class tb_usuario(rx.Model, table=True):
    tipo_usuario: str  # Esperado: "gestora" ou "investidor"
    nome_usuario: str
    email_usuario: str
    identificador_usuario: str
    senha_hash_usuario: str

class tb_aporte(rx.Model, table=True):
    cnpj: str
    nome_empresa: str
    valor_aporte: float
    categoria: str
    prazo: int
    taxa: float
    status_pagamento: str