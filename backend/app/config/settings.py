"""
Configuração da aplicação, lida do ambiente.

Único ponto do backend autorizado a ler variável de ambiente. O resto importa
`settings` daqui.

COMO FUNCIONA:
    1. O `.env` é carregado quando existe. Em produção as variáveis já vêm do
       ambiente e o arquivo não existe.
    2. Os campos são validados na primeira leitura.
    3. `obter_configuracao()` fica em cache: a leitura acontece uma vez por processo.

Args:
    Nenhum. A fonte é o ambiente.

Returns:
    Configuracao: instância única, via `obter_configuracao()`.

Raises:
    ValidationError: Se uma variável tiver tipo inválido.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracao(BaseSettings):
    """Variáveis de ambiente do backend, tipadas."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # JSON da service account inline, ou caminho de arquivo.
    google_application_credentials: str = ""
    project_id: str = "plataforma-clara"
    bigquery_dataset: str = "dados_cvm"

    redis_url: str = ""

    groq_api_key: str = ""
    llm_model_name: str = "groq:openai/gpt-oss-120b"
    llm_temperature: float = 0.1


@lru_cache
def obter_configuracao() -> Configuracao:
    """
    Devolve a configuração da aplicação, lida uma única vez por processo.

    Returns:
        Configuracao: Os valores já validados.
    """
    return Configuracao()


settings = obter_configuracao()
