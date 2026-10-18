"""Seed one generated local QA admin. Vendors are registered by browser tests."""
import json
from pathlib import Path
import secrets
from uuid import uuid4

from sqlalchemy.engine import make_url

from app.core.auth import hash_password
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.identity import User, UserRole


def main():
    settings = get_settings()
    url = make_url(settings.database_url)
    if settings.app_env not in {'development', 'test'} or url.host not in {'localhost', '127.0.0.1'}:
        raise SystemExit('Browser QA seed is limited to local development/test databases')
    if url.database not in {'vendorflow', 'vendorflow_test', 'vendorflow_e2e'}:
        raise SystemExit('Use a dedicated fictional VendorFlow database for browser QA')
    credentials = {'email': f'qa-admin-{uuid4().hex}@example.com', 'password': secrets.token_urlsafe(24)}
    with SessionLocal() as db:
        db.add(User(email=credentials['email'], full_name='Fictional QA Administrator',
                    password_hash=hash_password(credentials['password']), role=UserRole.ADMIN))
        db.commit()
    local = Path(__file__).resolve().parents[2] / '.local'
    local.mkdir(exist_ok=True)
    (local / 'browser-qa.json').write_text(json.dumps(credentials))
    print('Prepared local QA admin. Generated credentials remain in ignored .local/browser-qa.json.')


if __name__ == '__main__':
    main()
