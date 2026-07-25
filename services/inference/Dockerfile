FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OMP_NUM_THREADS=1 \
    OMP_WAIT_POLICY=PASSIVE \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

RUN addgroup --system slatesignal \
    && adduser --system --ingroup slatesignal slatesignal

COPY pyproject.toml README.md alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY data ./data
COPY artifacts ./artifacts

RUN pip install --no-cache-dir ".[runtime]" \
    && chown -R slatesignal:slatesignal /app

USER slatesignal

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=4s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT', '8000') + '/v1/health', timeout=3)"

CMD ["sh", "-c", "alembic upgrade head && uvicorn slatesignal.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
