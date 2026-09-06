"""
Configuração de logging do backend.

Chamado uma vez, no lifespan da aplicação. Antes disso, qualquer log emitido por
um módulo importado cai na configuração padrão do Python e some do stdout do
container.

COMO FUNCIONA:
    1. Define o formato e o nível a partir de `settings.log_nivel`.
    2. Silencia os loggers barulhentos de bibliotecas externas, que em DEBUG
       enchem o log com o corpo de cada requisição HTTP.
    3. `force=True` reconfigura handlers que uma biblioteca já tenha instalado —
       sem isso, quem chamou `basicConfig` primeiro vence.

Args:
    Nenhum.

Returns:
    None.
"""

import logging

from app.config.settings import settings

# Bibliotecas que logam demais no nível de INFO/DEBUG e não dizem nada útil
# sobre a nossa aplicação.
_LOGGERS_SILENCIADOS = (
    "urllib3",
    "google.auth",
    "google.cloud",
    "httpx",
    "httpcore",
)

_FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configurar_logging() -> None:
    """
    Aplica a configuração de logging do processo.

    Deve ser chamado no início do lifespan, antes de qualquer trabalho.
    """
    logging.basicConfig(
        level=settings.log_nivel.upper(),
        format=_FORMATO,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

    for nome in _LOGGERS_SILENCIADOS:
        logging.getLogger(nome).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging configurado (nível %s, ambiente %s).",
        settings.log_nivel.upper(),
        settings.ambiente,
    )
