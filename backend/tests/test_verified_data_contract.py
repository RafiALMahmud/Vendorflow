import json
from pathlib import Path

from app.contracts.verified_data import ReviewStatus, VerifiedVendorSnapshot


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "verified_vendor_snapshot.json"


def test_fictional_snapshot_matches_shared_contract() -> None:
    snapshot = VerifiedVendorSnapshot.model_validate_json(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )

    assert snapshot.company_name == "Example Trading Ltd"
    assert snapshot.documents[0].document_type == "trade_license"
    assert snapshot.documents[0].fields["expiry_date"].verified_value == "2026-12-31"


def test_unreviewed_ocr_value_is_not_verified() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    field = fixture["documents"][0]["fields"]["tax_identifier"]

    assert field["review_status"] == ReviewStatus.UNREVIEWED

    snapshot = VerifiedVendorSnapshot.model_validate(fixture)
    assert snapshot.documents[0].fields["tax_identifier"].verified_value is None
