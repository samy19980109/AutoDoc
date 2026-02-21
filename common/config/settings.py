from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    model_config = {"env_prefix": "AUTODOC_", "env_file": ".env", "extra": "ignore"}

    # Database
    database_url: str = "postgresql://autodoc:autodoc@localhost:5433/autodoc"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # GitHub
    github_webhook_secret: str = ""
    github_token: str = ""

    # AI Providers
    ai_provider: str = Field(default="anthropic", description="anthropic or openai")
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ai_model: str = "claude-sonnet-4-20250514"

    # Atlassian
    confluence_url: str = ""
    confluence_username: str = ""
    confluence_api_token: str = ""
    jira_url: str = ""
    jira_username: str = ""
    jira_api_token: str = ""

    # API Gateway
    api_secret_key: str = "change-me-in-production"
    api_key_header: str = "X-API-Key"
    api_keys: str = ""  # comma-separated valid API keys

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"


def get_settings() -> Settings:
    return Settings()
