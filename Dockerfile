FROM python:3.11-slim-bookworm@sha256:ee710afcfb733f4a750d9be683cf054b5cd247b6c5f5237a6849ea568b90ab15

LABEL org.opencontainers.image.title="xion-relay"
LABEL org.opencontainers.image.description="Xion orchestrator API / Relay runtime image"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# GPU-backed Ollama floor (Akash/Chutes) often needs >8s for first tokens; the
# repo default pin stays 8s for ``xion-verify cognition-loop-bounded``. Local
# runs can override with ``docker run -e XION_COGNITION_WALL_S=8``.
ENV XION_COGNITION_WALL_S=120

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY orchestrator ./orchestrator
COPY genesis/SOUL_PROMPT.md ./genesis/SOUL_PROMPT.md
COPY docker/entrypoint-xion-orchestrator-api.sh /usr/local/bin/entrypoint-xion-orchestrator-api.sh

RUN chmod +x /usr/local/bin/entrypoint-xion-orchestrator-api.sh \
    && python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir ".[api]"

RUN mkdir -p /app/data

EXPOSE 8000 8443

ENTRYPOINT ["/usr/local/bin/entrypoint-xion-orchestrator-api.sh"]
CMD []
