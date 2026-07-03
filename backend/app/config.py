from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    gemini_api_key: str
    database_url: str = "postgresql+psycopg://equi:equi@localhost:5433/equi_docintel"

    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/drive/oauth2callback"

    frontend_origin: str = "http://localhost:3000"

    generation_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    token_store_path: Path = ROOT_DIR / "backend" / "drive_token.json"


settings = Settings()
