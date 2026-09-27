"""
Erros de negócio da Plataforma Clara.

Existem para que a camada de serviço possa recusar uma operação sem depender de
como o resultado será exibido. O texto que o usuário lê é decidido por quem chama
— hoje um `rx.State`, na Fase 2 um `HTTPException` — e não fica preso aqui.
"""


class ErroDeNegocio(Exception):
    """Base de todos os erros de regra de negócio. Nunca levantada diretamente."""


class EmailJaCadastradoError(ErroDeNegocio):
    """O e-mail informado já pertence a outro usuário."""


class DocumentoInvalidoError(ErroDeNegocio):
    """O CPF/CNPJ informado não passou na validação estrutural."""


class DadosIncompletosError(ErroDeNegocio):
    """Faltam campos obrigatórios para concluir a operação."""
