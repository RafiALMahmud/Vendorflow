# Explainable document review rules

`assess_risk(VendorSnapshot, reference_date, RiskRules)` is pure and performs no
database, OCR, network, clock, or authorization operations. Its readiness score
is a completeness/consistency heuristic, never a fraud probability or decision.

The provisional v1 policy requires **trade_license and business_registration**.
The team specification does not select required types; confirm this policy with
Dev 1/product before integration. Tax certificates and other documents are optional.
Required types/deductions/version can be supplied through `RiskRules`.

| Finding code | Deduction | Evidence |
| --- | ---: | --- |
| missing_required_document | 30 | Missing required document type |
| expired_license | 25 | Verified trade-license expiry before reference date |
| confirmed_company_name_mismatch | 20 | Confirmed/corrected company differs from profile |
| missing_verified_registration | 15 | Required document registration lacks verified value |
| unverified_mandatory_field | 10 | License expiry absent/unverified/invalid; supplied company field unreviewed |

Registration is mandatory on each required document type; expiry is mandatory
on trade licenses. A company-name field is checked when supplied. Comparison
ignores case and repeated whitespace; no fuzzy matching or legal-name guessing.
Only `confirmed_value` with `confirmed`/`corrected` review state on a `processed`
document is trusted. Raw OCR and failed/in-progress extraction cannot assert an
expiry or mismatch. Invalid dates request verification and never assert expiry.
Expiry on the reference date is valid through that date.

Deduplicate by finding code, document type, and field, retaining all evidence IDs.
Registration absence receives 15 only, not an additional 10. Missing documents
receive no deductions for nonexistent fields. Duplicate evidence is not repeated;
multiple conflicting documents retain adverse findings rather than hide them.
Findings/evidence have stable ordering independent of document input order.

Clamp score to 0–100. 80–100: low_review_priority; 50–79:
medium_review_priority; 0–49: high_review_priority. Store rules version, reference
date and the complete assessment when submission integration becomes available.
The local Pydantic input boundary lives in Dev 2's `schemas/risk.py`; it is not a
competing snapshot builder. Reuse Dev 1's shared contract once merged and reviewed.
