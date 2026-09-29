from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_secret_key: str = "change-me-to-a-long-random-string"
    app_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"

    database_url: str = "sqlite:///./backend/data/accrue.db"

    retain_raw_input: bool = True
    max_escalation_chars: int = 20000
    analyze_rate_limit_per_minute: int = 30
    request_timeout_seconds: int = 45

    jwt_expire_minutes: int = 480
    demo_csm_email: str = "csm@accrue.demo"
    demo_csm_password: str = "AccrueDemo!2026"
    demo_admin_email: str = "admin@accrue.demo"
    demo_admin_password: str = "AccrueAdmin!2026"

    hindsight_mode: str = "mock"
    hindsight_base_url: str = "http://localhost:8888"
    hindsight_api_key: str = ""
    hindsight_timeout_seconds: int = 20

    llm_mode: str = "mock"
    llm_model: str = "openai/gpt-oss-120b"
    groq_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    llm_timeout_seconds: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.app_cors_origins.split(",") if item.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("sqlite:///./"):
            data_dir = ROOT / "backend" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{(data_dir / 'accrue.db').as_posix()}"
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
