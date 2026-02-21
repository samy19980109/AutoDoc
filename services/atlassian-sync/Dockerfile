FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY common/ common/
COPY services/atlassian-sync/ services/atlassian_sync/

EXPOSE 8002
CMD ["uvicorn", "services.atlassian_sync.main:app", "--host", "0.0.0.0", "--port", "8002"]
