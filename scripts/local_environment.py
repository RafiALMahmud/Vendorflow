"""Project-owned PostgreSQL/OCR setup. Never alters a system database or PATH."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tarfile
import urllib.request

from dotenv import dotenv_values, set_key
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'


def run(arguments, **kwargs):
    subprocess.run([str(arg) for arg in arguments], check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, **kwargs)


def configure(postgres_bin: Path, port: int, skip_ocr: bool):
    LOCAL.mkdir(exist_ok=True)
    envfile = ROOT / '.env'
    if not envfile.exists():
        shutil.copyfile(ROOT / '.env.example', envfile)
    state = LOCAL / 'postgres-config.json'
    if not state.exists():
        state.write_text(json.dumps({'admin_password': secrets.token_urlsafe(32),
                                     'app_password': secrets.token_urlsafe(32)}))
    credentials = json.loads(state.read_text())
    if credentials.get('port', port) != port:
        raise SystemExit('Use the existing project cluster port; changing it requires deliberate local configuration')
    credentials['port'] = port
    state.write_text(json.dumps(credentials))
    data = LOCAL / 'postgres'
    with (LOCAL / 'postgres-setup.log').open('a') as log:
        if not (data / 'PG_VERSION').exists():
            password_file = LOCAL / 'initdb-password.tmp'
            password_file.write_text(credentials['admin_password'])
            try:
                run([postgres_bin / 'initdb.exe', '-D', data, '-U', 'vendorflow_cluster',
                     '--pwfile', password_file, '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C'], stdout=log, stderr=log)
            finally:
                password_file.unlink(missing_ok=True)
        status = subprocess.run([str(postgres_bin / 'pg_ctl.exe'), '-D', str(data), 'status'],
                                stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        if status.returncode:
            run([postgres_bin / 'pg_ctl.exe', '-D', data, '-l', LOCAL / 'postgres.log',
                 '-o', f'-h 127.0.0.1 -p {port}', '-w', 'start'], stdout=log, stderr=log)
    with psycopg.connect(host='127.0.0.1', port=port, user='vendorflow_cluster',
                         password=credentials['admin_password'], dbname='postgres', autocommit=True) as db:
        if not db.execute("SELECT 1 FROM pg_roles WHERE rolname='vendorflow'").fetchone():
            db.execute(sql.SQL('CREATE ROLE vendorflow LOGIN PASSWORD {}').format(sql.Literal(credentials['app_password'])))
        for name in ('vendorflow', 'vendorflow_test', 'vendorflow_e2e'):
            if not db.execute('SELECT 1 FROM pg_database WHERE datname=%s', (name,)).fetchone():
                db.execute(sql.SQL('CREATE DATABASE {} OWNER vendorflow').format(sql.Identifier(name)))
    values = dotenv_values(envfile)
    for key, database in [('DATABASE_URL', 'vendorflow'), ('TEST_DATABASE_URL', 'vendorflow_test')]:
        if not values.get(key) or values[key].startswith('postgresql+psycopg://vendorflow:vendorflow@localhost:5432/'):
            set_key(envfile, key, f"postgresql+psycopg://vendorflow:{credentials['app_password']}@127.0.0.1:{port}/{database}")
    if values.get('JWT_SECRET_KEY') in (None, '', 'replace-with-at-least-32-random-characters'):
        set_key(envfile, 'JWT_SECRET_KEY', secrets.token_urlsafe(48))
    if not values.get('DOCUMENT_STORAGE_DIR') or values['DOCUMENT_STORAGE_DIR'] == 'private_uploads':
        set_key(envfile, 'DOCUMENT_STORAGE_DIR', str(LOCAL / 'private_uploads'))
    if not skip_ocr:
        install_ocr(envfile)
    print(f'Project PostgreSQL available on 127.0.0.1:{port}. Existing non-default configuration and secrets preserved.')


def install_ocr(envfile):
    binary = LOCAL / 'bin' / 'micromamba.exe'
    if not binary.exists():
        binary.parent.mkdir(exist_ok=True)
        archive = LOCAL / 'micromamba.tar.bz2'
        urllib.request.urlretrieve('https://micro.mamba.pm/api/micromamba/win-64/latest', archive)
        with tarfile.open(archive) as package:
            binary.write_bytes(package.extractfile('Library/bin/micromamba.exe').read())
    environment = dict(os.environ, MAMBA_ROOT_PREFIX=str(LOCAL / 'mamba'))
    tesseract = LOCAL / 'ocr' / 'Library' / 'bin' / 'tesseract.exe'
    if not tesseract.exists():
        run([binary, 'create', '-y', '--no-rc', '-p', LOCAL / 'ocr', '-c', 'conda-forge', 'tesseract'], env=environment)
    values = dotenv_values(envfile)
    if not values.get('TESSERACT_CMD'):
        set_key(envfile, 'TESSERACT_CMD', str(tesseract))
    if not values.get('TESSERACT_DATA_DIR'):
        set_key(envfile, 'TESSERACT_DATA_DIR', str(LOCAL / 'ocr' / 'share' / 'tessdata'))
    run([tesseract, '--version'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--postgres-bin', type=Path, required=True)
    parser.add_argument('--port', type=int, default=55432)
    parser.add_argument('--skip-ocr', action='store_true')
    options = parser.parse_args()
    os.chdir(ROOT)
    configure(options.postgres_bin.resolve(), options.port, options.skip_ocr)
