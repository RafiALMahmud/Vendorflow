# Setup report - 2026-10-19 (Asia/Dhaka)

Origin: https://github.com/RafiALMahmud/Vendorflow. Integration branch:
feat/complete-vendorflow-mvp. Tested implementation d8b4008; base a15d549.
No pre-existing work was discarded and no collaborator/main branch changed.

| Tool | Observed |
|---|---|
| OS / shell | Windows x64, PowerShell 5.1.26100.9444 |
| Python | 3.12.6; project-local .venv |
| Node / npm | 22.21.0 / 10.9.4 |
| Git | 2.48.1.windows.1 |
| PostgreSQL | 17.7; system 5432 untouched, project cluster 55432 |
| Tesseract | 5.5.3; project-local micromamba/conda-forge installation |
| Browser tests | Playwright 1.64.1, installed Edge locally; Chromium on CI |

Exact backend and frontend versions are in [backend-packages.json](evidence/backend-packages.json)
and [frontend-packages.json](evidence/frontend-packages.json). Main workstation:
FastAPI 0.143.5, Starlette 1.8.0, Pydantic 2.14.1, SQLAlchemy 2.1.5,
psycopg 3.3.6, Alembic 1.20.0, PyMuPDF 1.28.2, pytest 8.4.2.
Fresh setup resolved FastAPI 0.146.0/Starlette 1.9.0 within the existing manifest
ranges and also passed all checks. React 19.3.1, TypeScript 5.8.3, Vite 6.4.4,
Vitest 5.0.5, Tailwind 4.3.3 and ESLint 9.39.5 were verified.
Only the new browser-test dependency @playwright/test was added for release QA;
no existing package version was changed to hide a failure.

| Executed phase | Exit / observed result |
|---|---|
| pip install -e ./backend[dev] | 0; compatible existing .venv reused |
| pip check (workstation and fresh venv) | 0; no broken requirements |
| npm ci | First attempt EPERM because Vite held a native module; stopped recorded servers, reran: 0 |
| micromamba project-local Tesseract install | 0; 5.5.3, no administrator/system PATH change |
| real four-PDF extraction | 0; 23/23 exact expected fields, including 6 real scan OCR fields |
| PostgreSQL readiness and alembic check | 0; one head 0006_review, no schema drift |
| fresh Setup-Local.ps1 | 0; new venv, npm tree, SCRAM cluster and fresh schema |
| full migration downgrade/upgrade on empty fresh QA DB | 0 for heads/downgrade base/upgrade head/check |
| backend pytest with RUN_REAL_OCR=1 | 0; 182 passed, zero skipped |
| frontend test/lint/build | 0; 27 tests, lint/build pass |
| browser acceptance | 0; 2 scenarios passed on workstation and CI |

The [fresh-checkout evidence](evidence/fresh-checkout.json) records the actual GitHub
clone and commands. It used independent port 55433 and reused the installed OCR
binary via TESSERACT_CMD/TESSERACT_DATA_DIR with documented -SkipOcr. It did not
reuse .venv, node_modules, .env or a database from the working checkout. Its
PostgreSQL instance was stopped afterward. A separate migration round trip
confirmed the fresh development DB contained no rows before downgrade.

Generated database/JWT/app passwords remain ignored; existing non-default secrets
were preserved. Runtime-secret scan found no generated secrets in tracked files.
The original local vendor/admin account file remains private and unchanged.

Portable setup follows the [official micromamba Windows instructions](https://mamba.readthedocs.io/en/stable/installation/micromamba-installation.html)
and installs the [conda-forge Tesseract package](https://github.com/conda-forge/tesseract-feedstock).
Windows portable Tesseract requires its explicit language-data directory, which
setup configures. No paid API or global software installer was used.

Use README.md for exact setup/start/stop/admin-seed/test PowerShell commands.
There are no remaining local MVP dependency or credential blockers.
