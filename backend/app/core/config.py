from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DEFAULT_UPLOAD_DIR = REPO_ROOT / "uploads"
DEFAULT_DATABASE_URL = f"sqlite:///{(DEFAULT_DATA_DIR / 'app.db').as_posix()}"


class Settings(BaseSettings):
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/api"
    database_url: str = DEFAULT_DATABASE_URL
    upload_dir: str = str(DEFAULT_UPLOAD_DIR)
    log_level: str = "INFO"
    llm_mock_mode: bool = True
    formula_llm_api_url: str = "https://example.invalid/v1/formula-infer"
    formula_llm_api_key: str = ""
    formula_llm_model: str = "mock/day13"
    formula_prompt_version: str = "day13_v1"
    analysis_llm_api_url: str = "https://example.invalid/v1/analyze"
    analysis_llm_api_key: str = ""
    analysis_llm_model: str = "mock/day20"
    analysis_prompt_version: str = "day20_v1"

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()