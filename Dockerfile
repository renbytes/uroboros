# Use Python 3.11 Slim (Debian Bookworm) for a small footprint
FROM python:3.11-slim-bookworm

# Set Environment Variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files
# PYTHONUNBUFFERED: Ensures logs are streamed directly to container output (vital for E2B/Arbiter logs)
# POETRY_NO_INTERACTION: Prevents Poetry from asking interactive questions
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH=/app/src

# Set working directory
WORKDIR /app

# Install System Dependencies
# curl: for installing poetry (if not using pip)
# git: required for agents to perform git operations or install git-based deps
# build-essential: for compiling C extensions in python packages
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry via pip
RUN pip install "poetry==$POETRY_VERSION"

# Copy Dependency Files ONLY (Layer Caching Strategy)
# We copy these first so that if only code changes, we don't re-install dependencies
COPY pyproject.toml poetry.lock ./

# Install Dependencies
# --no-root: Don't install the project package itself yet (we do that next)
# --only main: Don't install dev dependencies (like pytest/linting) in production image
RUN poetry install --no-root --only main

# Copy Application Code
COPY src ./src
COPY .env.example .env

# Create data directory for local vector db persistence
RUN mkdir -p data/chromadb

# Create a non-root user for security (Best Practice)
RUN addgroup --system uroboros && adduser --system --group uroboros
RUN chown -R uroboros:uroboros /app
USER uroboros

# Entrypoint
# We run the module directly
CMD ["python", "-m", "uroboros.main", "--loop"]
