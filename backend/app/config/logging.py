"""
Configuração de logging do backend.

Chamado uma vez, no lifespan. Antes disso, log emitido por módulo já importado cai
na configuração padrão do Python e some do stdout do container.

COMO FUNCIONA:
    1. Define formato e nível.
    2. Silencia os loggers de bibliotecas externas.
    3. `force=True` reconfigura handlers que alguma biblioteca já tenha instalado.

Args:
    Nenhum.

Returns:
    None.
"""

import logging

# Bibliotecas barulhentas demais em INFO/DEBUG.
_LOGGERS_SILENCIADOS = (
    "urllib3",
    "google.auth",
    "google.cloud",
    "httpx",
    "httpcore",
)

_FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configurar_logging() -> None:
    """Aplica a configuração de logging do processo."""
    logging.basicConfig(
        level=logging.INFO,
        format=_FORMATO,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

    for nome in _LOGGERS_SILENCIADOS:
        logging.getLogger(nome).setLevel(logging.WARNING)
