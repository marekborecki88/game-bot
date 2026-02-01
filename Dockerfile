# Use Python 3.14 base (install Playwright browsers later)
FROM python:3.14-slim

LABEL maintainer="marek.borecki <marekborecki88>"

# Environment - make Python behave and configure Poetry
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/opt/poetry/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH="/ms-playwright" \
    HEADLESS=true

WORKDIR /app

# Install curl and install Poetry using the official installer
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg && \
    curl -sSL https://install.python-poetry.org | python3 - --version "$POETRY_VERSION" && \
    if [ -f "/opt/poetry/bin/poetry" ]; then ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry; fi && \
    apt-get purge -y --auto-remove curl gnupg && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency definitions first (for caching)
COPY pyproject.toml poetry.lock ./

# Copy project metadata needed by Poetry (README referenced in pyproject)
COPY README.md ./

# Copy package source so `poetry install` can install the project (register console script)
COPY src ./src

# Install project dependencies and Playwright system deps in one layer
RUN poetry install --no-interaction --no-ansi && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libx11-6 \
        libxcomposite1 \
        libxrandr2 \
        libgbm1 \
        libgtk-3-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libexpat1 \
        libxcb1 \
        libxdamage1 \
        libxfixes3 \
        libxext6 \
        fonts-liberation \
        fonts-noto-color-emoji && \
    rm -rf /var/lib/apt/lists/* && \
    poetry run playwright install --with-deps chromium || true

# Copy application source
COPY . .

# Create a dedicated, non-root user and set permissions
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app \
    && mkdir -p /ms-playwright \
    && chown -R appuser:appuser /ms-playwright
USER appuser

# Default command: run the installed console script via Poetry (poetry run game-bot)
CMD ["poetry", "run", "game-bot"]
