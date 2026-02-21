FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY common/ common/
COPY services/doc-processor/ services/doc_processor/

ENV PYTHONPATH=/app:/app/services/doc_processor

CMD ["celery", "-A", "celery_app:app", "worker", "--loglevel=info", "--concurrency=2", "--include=tasks"]
