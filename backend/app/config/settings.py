"""
Configuração central da aplicação, lida do ambiente.

Único ponto do backend autorizado a ler variável de ambiente. Todo o resto importa
`settings` daqui — assim uma variável renomeada quebra em um lugar só, e um teste
consegue substituir a configuração inteira sem mexer em `os.environ`.

COMO FUNCIONA:
    1. O `.env` é carregado quando existe (desenvolvimento local). Em produção, no
       Railway, as variáveis já vêm do ambiente e o arquivo não existe.
    2. Os campos são validados pelo Pydantic na primeira leitura: uma variável
       obrigatória ausente falha na subida da aplicação, não no meio de uma
       requisição.
    3. `obter_configuracao()` fica em cache — a leitura acontece uma vez por processo.

Args:
    Nenhum. A fonte é o ambiente.

Returns:
    Configuracao: instância única, via `obter_configuracao()`.

Raises:
    ValidationError: Se uma variável obrigatória faltar ou tiver tipo inválido.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracao(BaseSettings):
    """
    Variáveis de ambiente do backend, tipadas.

    Os campos sem valor padrão são obrigatórios: a aplicação não sobe sem eles.
    Os que têm padrão são opcionais e seguros para desenvolvimento local.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # variáveis do Railway que não são nossas não derrubam a subida
    )

    # --- Aplicação ---
    ambiente: Literal["local", "producao"] = "local"
    log_nivel: str = "INFO"

    # As origens que podem chamar a API. Em produção é a URL do frontend no Railway;
    # sem isso o browser bloqueia a chamada antes de ela sair.
    cors_origens: list[str] = ["http://localhost:5173"]

    # --- Google Cloud ---
    # Aceita o JSON da service account inline ou o caminho de um arquivo.
    google_application_credentials: str = ""
    gcp_projeto_id: str = "plataforma-clara"
    bigquery_dataset: str = "dados_fidc"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Groq (relatório por IA) ---
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
