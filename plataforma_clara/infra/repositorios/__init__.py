"""
Repositórios de acesso ao PostgreSQL.

Cada repositório recebe uma `Session` do SQLAlchemy pronta e devolve objetos de
domínio. Nenhum deles abre sessão por conta própria nem engole exceções: quem
decide o escopo da transação e o que fazer com a falha é a camada de serviço.
"""
