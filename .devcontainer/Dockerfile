FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

COPY --from=ghcr.io/astral-sh/ruff:latest /ruff /usr/local/bin/ruff
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /workspace