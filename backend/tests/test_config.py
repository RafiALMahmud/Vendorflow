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
