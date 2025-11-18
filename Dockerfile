# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create non-root user (using Debian-compatible command)
RUN adduser --disabled-password --gecos "" myuser && \
    chown -R myuser:myuser /app

USER myuser

# Set PATH for user's local bin
ENV PATH="/home/myuser/.local/bin:$PATH"

# Run the application
CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port $PORT"]
