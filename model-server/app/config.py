from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Model server configuration loaded from environment variables."""

    model_server_host: str = "0.0.0.0"
    model_server_port: int = 8001
    mock_models: bool = False

    # Live model provider configuration
    geochat_model_path: str = ""
    teochat_model_path: str = ""
    sam2_checkpoint_path: str = ""
    huggingface_api_key: str = ""
    gemini_api_key: str = ""
    teochat_api_url: str = ""
    teochat_api_key: str = ""
    open_router_api_key: str = ""
    open_router_base_url: str = "https://openrouter.ai/api/v1"
    vision_language_model: str = "qwen/qwen-2.5-vl-7b-instruct:free"
    
    # Local fallback/primary model configuration
    model_backend: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5vl:7b"

    # Cloudflare Workers AI configuration
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cf_account_id: str = ""
    cf_api_token: str = ""

    class Config:
        env_file = ".env"
        protected_namespaces = ()
        extra = "allow"


settings = Settings()

