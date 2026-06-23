"""Configuración de la app vía variables de entorno (.env) con pydantic-settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "production"
    host: str = "127.0.0.1"
    port: int = 8091
    db_path: str = "./data/app.db"
    session_secret: str = ""
    cookie_secure: bool = True

    # Solo usados por el seed
    admin_email: str = ""
    admin_password: str = ""

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() in {"dev", "development", "local"}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.session_secret:
        # La sesión se firma con este secreto; sin él la app es insegura. No arrancar.
        raise RuntimeError(
            "SESSION_SECRET no está definido. Genera uno con `openssl rand -hex 32` "
            "y ponlo en el archivo .env antes de arrancar."
        )
    return settings


settings = get_settings()
