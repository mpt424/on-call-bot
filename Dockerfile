FROM python:3.11 AS base
EXPOSE 8080
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_HOME="/opt/poetry" \
    PATH=/opt/poetry/bin:$PATH \
    HOSTNAME=0.0.0.0

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN (curl -sSL https://install.python-poetry.org | python -) && mkdir -p /app && useradd -ms /bin/bash user && chown -R user:user /app && chmod 755 /app
WORKDIR /app
COPY pyproject.toml poetry.lock poetry.toml /app/
RUN poetry export -o requirements.txt --without-hashes && pip install -r requirements.txt

FROM base as app
USER user

COPY langs /app/langs
COPY on_call_bot /app/on_call_bot
COPY resources /app/resources
ENV TZ=Asia/Jerusalem

CMD ["python", "-m", "on_call_bot"]
