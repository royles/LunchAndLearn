from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.paths import resolve_project_root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8090

    project_root: Path = resolve_project_root()
    state_db_path: Path | None = None
    frontend_dist: Path | None = None

    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_api_key: str = "not-needed"
    llm_model: str = "llama3.2"
    llm_max_tokens: int = 4096

    # Optional Fernet key (url-safe base64). If unset, a key is stored under data/.
    model_token_encryption_key: str = ""
    model_token_encryption_key_file: Path | None = None

    @property
    def database_url(self) -> str:
        db_path = self.state_db_path or (self.project_root / "data" / "state.db")
        return f"sqlite:///{db_path.resolve()}"

    @property
    def static_dir(self) -> Path:
        return self.frontend_dist or (self.project_root / "frontend" / "dist")

    def resolve_port(self) -> int:
        import os

        for key in ("CDSW_APP_PORT", "CDSW_READONLY_PORT"):
            raw = os.environ.get(key)
            if raw:
                return int(raw)
        return self.port


settings = Settings()
