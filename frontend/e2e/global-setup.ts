import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

export default function setup() {
  const root = path.resolve('..');
  const localPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const python = process.env.VENDORFLOW_PYTHON ?? (existsSync(localPython) ? localPython : 'python');
  execFileSync(python, ['-m', 'scripts.prepare_browser_qa'], { cwd: path.join(root, 'backend'), stdio: 'pipe' });
}
