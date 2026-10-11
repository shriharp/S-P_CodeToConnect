FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    INGESTION_SCHEDULER_ENABLED=true \
    INGESTION_INTERVAL_SECONDS=90

WORKDIR /app

RUN addgroup --system kairos && adduser --system --ingroup kairos kairos

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend/app ./app
COPY backend/pyproject.toml ./pyproject.toml
COPY data /opt/kairos-seed-data
COPY backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN mkdir -p /app/data /app/recordings && ln -s /app/data /data && chown -R kairos:kairos /app /opt/kairos-seed-data /usr/local/bin/docker-entrypoint.sh

USER kairos

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/live/health', timeout=3)"

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
