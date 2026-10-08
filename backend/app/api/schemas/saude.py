"""
Contrato de resposta do healthcheck.

COMO FUNCIONA:
    1. `RespostaSaude` é o `response_model` de `GET /health`.
    2. O FastAPI valida o retorno do handler contra ele e o publica no OpenAPI.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from pydantic import BaseModel, Field


class RespostaSaude(BaseModel):
    """Estado do processo da API, sem consultar serviço externo."""

    status: str = Field(description="'ok' enquanto o processo atende requisições")
    versao: str = Field(description="Versão da API")
