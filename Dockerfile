# Imagem da aplicação Reflex (frontend compilado + backend FastAPI no mesmo processo).
#
# Python 3.12 é deliberado: o requirements.txt fixa pandas~=2.3.3, que ainda não tem
# wheel para 3.14 (a build de dependências transitivas falha). Manter alinhado com a
# versão usada na CI para que "passou local" signifique "passa na CI".

FROM python:3.12-slim AS base

# PYTHONUNBUFFERED garante que os logs apareçam em tempo real no docker logs,
# sem ficar presos no buffer de stdout.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl e unzip são exigidos pelo Reflex para baixar o Bun na primeira execução
# (ele compila o frontend React); build-essential cobre pacotes sem wheel pronta.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# Copiamos apenas os requirements antes do código-fonte: enquanto as dependências
# não mudarem, o Docker reaproveita esta camada e o rebuild fica muito mais rápido.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 3000 = frontend Reflex, 8000 = backend FastAPI/WebSocket.
EXPOSE 3000 8000

CMD ["reflex", "run", "--env", "prod", "--backend-host", "0.0.0.0"]
