from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

INSECURE_JWT_SECRETS = {
    "development-only-change-this-secret-before-deployment",
    "replace-with-at-least-32-random-characters",
}


class Settings(BaseSettings):
    app_name: str = "VendorFlow AI"
    app_env: str = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+psycopg://vendorflow:vendorflow@localhost:5432/vendorflow"
    )
    test_database_url: str = (
        "postgresql+psycopg://vendorflow:vendorflow@localhost:5432/vendorflow_test"
    )
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    jwt_secret_key: SecretStr = SecretStr(
        "development-only-change-this-secret-before-deployment"
    )
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def reject_development_jwt_secret_outside_local_environments(self) -> "Settings":
        secret = self.jwt_secret_key.get_secret_value()
        if len(secret) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
        if self.app_env not in {"development", "test"} and secret in INSECURE_JWT_SECRETS:
            raise ValueError("JWT_SECRET_KEY must be configured outside development/test")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

