FROM python:3.12-slim

# Evitar gravação de arquivos .pyc e garantir logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configurações do Streamlit
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

# Instalar o Poetry
RUN pip install --no-cache-dir poetry

# Copiar arquivos de configuração de dependências primeiro (aproveita cache do Docker)
COPY pyproject.toml poetry.lock* /app/

# Configurar Poetry para instalar dependências globais do container
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copiar os arquivos restantes do projeto
COPY . /app/

EXPOSE 8080

ENTRYPOINT ["streamlit", "run", "app.py"]