from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables."""

    database_url: str = "postgresql+asyncpg://satquery:satquery_dev_password@db:5432/satquery"
    model_server_url: str = "http://model-server:8001"
    upload_dir: str = "/app/uploads"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Max upload size (50MB)
    max_upload_size: int = 50 * 1024 * 1024

    class Config:
        env_file = ".env"


settings = Settings()
