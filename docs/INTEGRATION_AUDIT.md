# Integration audit - 2026-10-19 (Asia/Dhaka)

Remote: https://github.com/RafiALMahmud/Vendorflow. Clean initial checkout; no work discarded.
Chosen base: `a15d5498e710e2f02f2521f5d6c77e6251888074` on origin/feat/dev2-risk-review.
New branch: `feat/complete-vendorflow-mvp`. This base already merges D1 tip `04b8cf4` with D2 history; all remote tips below are ancestors. No duplicate merge/cherry-pick was needed. Main remains `aa591b8`.

## Current remote branch provenance

| Branch | SHA | Included in base |
|---|---|---|
| origin | `aa591b8d8d2c62fe4fb5f903065a31c7a63bed8b` | True |
| origin/chore/d1-release-prep | `04b8cf4db2b36b67757dd20ab7e141161c581143` | True |
| origin/feat/bootstrap | `883a2e55be7abc5873b73794fc1d2106c231b519` | True |
| origin/feat/dev2-risk-review | `a15d5498e710e2f02f2521f5d6c77e6251888074` | True |
| origin/feat/document-extraction | `7937b15b0a3f6dbb56cde40854129f219cbd4c3b` | True |
| origin/feat/document-upload | `2e3a6a84fc136b3985246c6e23ac526ef0e38481` | True |
| origin/feat/extracted-field-review | `4eed4217842292af86c3153566b72947e6e84022` | True |
| origin/feat/vendor-auth | `a63e0c011838ae536378136dfbac6bae966e11f5` | True |
| origin/feat/vendor-profile | `b89192d48d2ba55814dd3d944a016f823c79286c` | True |
| origin/feat/vendor-ui | `a7fb95819159a30ad3f9e0bde86c892a59133de7` | True |
| origin/feat/verified-snapshot-contract | `0c2de7d7ce14441b4e7ca9cc802b4d013b327668` | True |
| origin/main | `aa591b8d8d2c62fe4fb5f903065a31c7a63bed8b` | True |
| origin/test/document-quality | `393e72022746124cc70b3a72fb55ccf7f8c0cf28` | True |

## Pull requests observed

All nine D1 PRs remain OPEN and unmerged. No PR was merged or closed during this work.
| PR | Base | Head | SHA |
|---|---|---|---|
| [#1](https://github.com/RafiALMahmud/Vendorflow/pull/1) | main | feat/bootstrap | `883a2e55be7abc5873b73794fc1d2106c231b519` |
| [#2](https://github.com/RafiALMahmud/Vendorflow/pull/2) | feat/bootstrap | feat/vendor-auth | `a63e0c011838ae536378136dfbac6bae966e11f5` |
| [#3](https://github.com/RafiALMahmud/Vendorflow/pull/3) | feat/vendor-auth | feat/vendor-profile | `b89192d48d2ba55814dd3d944a016f823c79286c` |
| [#4](https://github.com/RafiALMahmud/Vendorflow/pull/4) | feat/vendor-profile | feat/document-upload | `2e3a6a84fc136b3985246c6e23ac526ef0e38481` |
| [#5](https://github.com/RafiALMahmud/Vendorflow/pull/5) | feat/document-upload | feat/document-extraction | `7937b15b0a3f6dbb56cde40854129f219cbd4c3b` |
| [#6](https://github.com/RafiALMahmud/Vendorflow/pull/6) | feat/extracted-field-review | feat/verified-snapshot-contract | `0c2de7d7ce14441b4e7ca9cc802b4d013b327668` |
| [#7](https://github.com/RafiALMahmud/Vendorflow/pull/7) | feat/verified-snapshot-contract | feat/vendor-ui | `a7fb95819159a30ad3f9e0bde86c892a59133de7` |
| [#8](https://github.com/RafiALMahmud/Vendorflow/pull/8) | feat/vendor-ui | test/document-quality | `393e72022746124cc70b3a72fb55ccf7f8c0cf28` |
| [#9](https://github.com/RafiALMahmud/Vendorflow/pull/9) | test/document-quality | chore/d1-release-prep | `04b8cf4db2b36b67757dd20ab7e141161c581143` |

PR #6 is based on the additional extracted-field-review branch (4eed421), which is also included in the base.

## Authorship and baseline

- D1 original: identity, vendors, storage, OCR/extraction, field review, verified contract, vendor UI, migrations 0001-0005 and associated tests.
- D2 original: risk/workflow/review persistence, admin/applications APIs/UI, migration 0006 and associated tests; merge a15d549 integrated both histories.
- This run: release fixture parser fixes, certificate-number support, real OCR setup/verification, session expiry, secure original evidence access, failed extraction retry, confirmation dialogs, reproducible setup/browser QA and release documentation.
- Baseline backend: 172 passed. Frontend: 24 passed, lint/build passed. Initial npm ci encountered a Vite-held Windows native-module lock; stopped only the recorded project servers and reran npm ci successfully. No dependency versions were changed to hide errors.
- Integration conflicts: none in this run. The four historical conflicts were resolved in a15d549; that commit remains intact.

## Release evidence

See FEATURE_CHECKLIST.md, QA_RESULTS.md, SETUP_REPORT.md and evidence/ocr-results.json for final commands and acceptance results.
