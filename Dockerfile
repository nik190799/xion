FROM python:3.11-slim-bookworm@sha256:ee710afcfb733f4a750d9be683cf054b5cd247b6c5f5237a6849ea568b90ab15

LABEL org.opencontainers.image.title="xion-relay"
LABEL org.opencontainers.image.description="Xion orchestrator API / Relay runtime image"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY orchestrator ./orchestrator

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir ".[api]"

EXPOSE 8000

ENTRYPOINT ["xion-orchestrator-api"]
