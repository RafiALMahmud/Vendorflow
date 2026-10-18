import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
const localPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.VENDORFLOW_PYTHON ?? (existsSync(localPython) ? localPython : 'python');

export default defineConfig({
  testDir: './e2e', workers: 1, timeout: 180_000, fullyParallel: false,
  globalSetup: './e2e/global-setup.ts',
  reporter: [['list'], ['json', { outputFile: '../.local/browser-results.json' }]],
  use: {
    baseURL: 'http://localhost:5173', browserName: 'chromium',
    actionTimeout: 15_000, navigationTimeout: 30_000,
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure',
    // Authentication headers/passwords must not be captured in shared traces.
    trace: 'off',
  },
  webServer: [
    { command: `"${python}" -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8000`,
      url: 'http://127.0.0.1:8000/api/v1/health', reuseExistingServer: !process.env.CI, timeout: 60_000 },
    { command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI, timeout: 60_000 },
  ],
});
