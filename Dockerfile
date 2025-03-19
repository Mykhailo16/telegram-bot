FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.4.0 /uv /bin/uv

ENV PYTHONUNBUFFERED=1
ENV UV_HTTP_TIMEOUT=120

WORKDIR /app

# Copy the application into the container.
COPY bot.py /app
COPY requirements.txt /app
COPY pyproject.toml /app

# Install the application dependencies.
RUN uv lock
RUN uv sync --frozen --no-dev --compile-bytecode

EXPOSE 8443