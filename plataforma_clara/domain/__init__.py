"""
Camada de domínio da Plataforma Clara.

Contém as regras de negócio, os modelos de tabela e os contratos de dados —
tudo sem nenhuma dependência de framework web. Nenhum módulo deste pacote pode
importar `reflex`, `fastapi` ou qualquer outra camada de entrega: é essa
restrição que permite que o domínio sobreviva intacto à migração para FastAPI.
"""
