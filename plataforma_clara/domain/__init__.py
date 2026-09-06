"""
Camada de domínio da Plataforma Clara.

Contém as regras de negócio, os modelos de tabela e os contratos de dados —
tudo sem nenhuma dependência de framework web. Nenhum módulo deste pacote pode
importar `fastapi` nem qualquer outra camada de entrega: é essa restrição que
permite trocar de camada de entrega sem tocar nas regras de negócio.
"""
