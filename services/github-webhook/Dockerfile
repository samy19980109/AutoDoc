FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY common/ common/
COPY services/github-webhook/ services/github_webhook/

EXPOSE 8001
CMD ["uvicorn", "services.github_webhook.main:app", "--host", "0.0.0.0", "--port", "8001"]
