FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

WORKDIR /app

# System dependencies (compilation of some wheels) - curl is used by the healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user; the database folder must be writable by it
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/Server/database \
    && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/Server

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:5000/docs > /dev/null || exit 1

# --preload: the app (and db.create_all) is initialised once, before the workers fork.
# One worker is the safe default with SQLite (single writer).
CMD ["gunicorn", "--preload", "--workers", "1", "--threads", "4", "--timeout", "60", \
     "--bind", "0.0.0.0:5000", "wsgi:app"]
