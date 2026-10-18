"""Live baseline smoke check after npm run build; stops both child processes."""
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def read(url, origin=None):
    request = Request(url, headers={'Origin': origin} if origin else {})
    with urlopen(request, timeout=2) as response:
        return response.read().decode(), response.headers


def ready(url, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError(f'Server exited with code {process.returncode}')
        try:
            return read(url)[0]
        except (URLError, TimeoutError):
            time.sleep(0.15)
    raise RuntimeError(f'Server did not become ready: {url}')


def main():
    backend_port, frontend_port = free_port(), free_port()
    processes = []
    try:
        processes.append(subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
            '--port', str(backend_port)], cwd=ROOT / 'backend',
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        health_url = f'http://127.0.0.1:{backend_port}/api/v1/health'
        health = json.loads(ready(health_url, processes[-1]))
        assert health['status'] == 'ok'
        _, headers = read(health_url, 'http://localhost:5173')
        assert headers['access-control-allow-origin'] == 'http://localhost:5173'
        print('PASS: live FastAPI health and configured frontend CORS')
        processes.append(subprocess.Popen([
            shutil.which('node'), 'node_modules/vite/bin/vite.js', 'preview',
            '--host', '127.0.0.1', '--port', str(frontend_port), '--strictPort'],
            cwd=ROOT / 'frontend', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        frontend_url = f'http://127.0.0.1:{frontend_port}'
        html = ready(frontend_url, processes[-1])
        assert '<div id="root">' in html
        assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
        assert assets
        for asset in assets:
            body, _ = read(frontend_url + asset)
            assert body
        print('PASS: live Vite production HTML and bundled assets')
        print('Browser rendering and authenticated review integration are not covered by this check.')
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
