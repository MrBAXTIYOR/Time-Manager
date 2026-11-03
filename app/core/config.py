"""Application configuration.

All configuration comes from environment variables (12-factor). Secrets have
NO defaults on purpose: the app refuses to start if they are missing.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, RedisDsn, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env also holds docker-only vars (MYSQL_ROOT_PASSWORD...)
    )

    # --- application ---
    app_name: str = "Time Management System"
    app_version: str = "0.1.0"
    app_env: Literal["development", "testing", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_v1_prefix: str = "/api/v1"

    # --- MySQL ---
    mysql_host: str = "localhost"
    mysql_port: int = Field(default=3306, ge=1, le=65535)
    mysql_user: str
    mysql_password: SecretStr  # required, no default
    mysql_database: str
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_recycle_seconds: int = 1800  # MySQL closes idle connections (wait_timeout)
    db_echo: bool = False

    # --- Redis ---
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def database_url(self) -> URL:
        """Built with URL.create so special characters in the password are
        escaped correctly (string formatting would break on '@' or '/')."""
        return URL.create(
            drivername="mysql+aiomysql",
            username=self.mysql_user,
            password=self.mysql_password.get_secret_value(),
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
