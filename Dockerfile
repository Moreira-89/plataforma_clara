# Imagem do backend da Plataforma Clara.
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

# build-essential cobre os pacotes sem wheel pronta. O curl e o unzip saíram junto
# com o Reflex — eram para baixar o Bun e compilar o frontend React.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiamos apenas os requirements antes do código-fonte: enquanto as dependências
# não mudarem, o Docker reaproveita esta camada e o rebuild fica muito mais rápido.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# SEM COMANDO DE EXECUÇÃO AINDA: o entry point saiu junto com o Reflex e o novo
# depende da estrutura de pastas a definir. Assim que o módulo da API existir,
# esta linha vira algo como:
#
#   CMD ["uvicorn", "<pacote>.main:app", "--host", "0.0.0.0", "--port", "8000"]
#
# Até lá a imagem constrói e serve para rodar a suíte e os comandos do Alembic,
# mas não sobe servidor nenhum.
CMD ["python", "-c", "raise SystemExit('Defina o entry point da API antes de subir o container.')"]
