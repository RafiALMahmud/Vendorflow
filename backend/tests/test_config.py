import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_origins_are_loaded_from_comma_separated_environment(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:5173, https://vendorflow.example",
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:5173",
        "https://vendorflow.example",
    ]


def test_production_rejects_documented_placeholder_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be configured"):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret_key="replace-with-at-least-32-random-characters",
        )


def test_short_jwt_secret_is_rejected_in_every_environment() -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(_env_file=None, jwt_secret_key="too-short")
