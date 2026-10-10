"""
Configuração da aplicação, lida do ambiente.

Único ponto do backend autorizado a ler variável de ambiente. O resto importa
`settings` daqui.

COMO FUNCIONA:
    1. O `backend/.env` é carregado quando existe. Em produção as variáveis já vêm do
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
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# O .env fica em backend/, qualquer que seja o diretório de onde o comando roda.
_ENV_ARQUIVO = Path(__file__).resolve().parents[2] / ".env"


class Configuracao(BaseSettings):
    """Variáveis de ambiente do backend, tipadas."""

    model_config = SettingsConfigDict(
        env_file=_ENV_ARQUIVO,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # JSON da service account inline, ou caminho de arquivo.
    google_application_credentials: str = ""
    project_id: str = "plataforma-clara"
    bigquery_dataset: str = "tabelas_silvers"

    # Origens que podem chamar a API, separadas por vírgula.
    cors_origens: str = "http://localhost:5173"

    redis_url: str = ""

    groq_api_key: SecretStr = SecretStr("")
    llm_model_name: str = "groq:openai/gpt-oss-120b"
    llm_temperature: float = 0.1


    @property
    def origens_cors(self) -> list[str]:
        """Origens liberadas no CORS, já separadas e sem espaços."""
        return [origem.strip() for origem in self.cors_origens.split(",") if origem.strip()]


@lru_cache
def obter_configuracao() -> Configuracao:
    """
    Devolve a configuração da aplicação, lida uma única vez por processo.

    Returns:
        Configuracao: Os valores já validados.
    """
    return Configuracao()


settings = obter_configuracao()
