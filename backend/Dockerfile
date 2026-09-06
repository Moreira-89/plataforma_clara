# Imagem do serviço de backend. No Railway, este serviço aponta o root directory
# para `backend/`, então o contexto de build é esta pasta.
#
# Python 3.12 é deliberado: o requirements.txt fixa pandas~=2.3.3, que ainda não
# tem wheel para 3.14. Manter alinhado com a CI para que "passou local" signifique
# "passa na CI".

FROM python:3.12-slim

# PYTHONUNBUFFERED garante que os logs apareçam em tempo real no docker logs,
# sem ficar presos no buffer de stdout.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# build-essential cobre os pacotes sem wheel pronta.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Os requirements vêm antes do código: enquanto as dependências não mudarem, o
# Docker reaproveita esta camada e o rebuild fica muito mais rápido.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# $PORT é injetado pelo Railway; 8000 é o padrão local.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
