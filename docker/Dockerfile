# syntax=docker/dockerfile:1

FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Development stage (VS Code Dev Container + Git/SSH) ---
FROM base AS dev

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update && apt-get install -y --no-install-recommends \
        git \
        openssh-client \
        sudo \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/* \
    && chown -R $USERNAME:$USERNAME /workspace

USER $USERNAME

# --- Builder stage (Production wheels) ---
FROM base AS builder

COPY requirements.txt .
RUN pip wheel --wheel-dir=/wheels -r requirements.txt

# --- Production runtime stage (Render / Deployment) ---
FROM base AS prod

RUN groupadd -r django && useradd -r -g django django

COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels

COPY --chown=django:django . /workspace
COPY --chown=django:django docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER django
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
