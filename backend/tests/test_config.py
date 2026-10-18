import pytest

from app.core.config import Settings


@pytest.mark.parametrize('value', [
    'http://localhost:5173, http://localhost:4173',
    '["http://localhost:5173", "http://localhost:4173"]',
])
def test_cors_origins_from_environment(monkeypatch, value):
    monkeypatch.setenv('CORS_ORIGINS', value)
    assert Settings(_env_file=None).cors_origins == [
        'http://localhost:5173', 'http://localhost:4173']
