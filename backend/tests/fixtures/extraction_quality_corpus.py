"""Purely fictional documents and ground truth for extraction evaluation."""

from dataclasses import dataclass
from io import BytesIO

import pymupdf
from PIL import Image, ImageDraw, ImageFont


FIELD_NAMES = (
    "company_name",
    "registration_number",
    "license_number",
    "issue_date",
    "expiry_date",
    "tax_identifier",
)


@dataclass(frozen=True)
class FictionalQualityDocument:
    name: str
    filename: str
    mime_type: str
    source_text: str
    expected: dict[str, str]
    requires_ocr: bool
    format: str


QUALITY_DOCUMENTS = (
    FictionalQualityDocument(
        name="alpha_trade_license",
        filename="alpha-trade-license.pdf",
        mime_type="application/pdf",
        source_text="""Company Name: Alpha Fictional Imports Ltd
Registration Number: REG-ALPHA-1001
License Number: LIC-ALPHA-2001
Issue Date: 17 October 2026
Expiry Date: 2027-10-16
Tax Identifier: TAX-ALPHA-3001""",
        expected={
            "company_name": "Alpha Fictional Imports Ltd",
            "registration_number": "REG-ALPHA-1001",
            "license_number": "LIC-ALPHA-2001",
            "issue_date": "2026-10-17",
            "expiry_date": "2027-10-16",
            "tax_identifier": "TAX-ALPHA-3001",
        },
        requires_ocr=False,
        format="digital_pdf",
    ),
    FictionalQualityDocument(
        name="beta_business_registration",
        filename="beta-business-registration.pdf",
        mime_type="application/pdf",
        source_text="""Business Name: Beta Imaginary Services PLC
Reg No: REG-BETA-1002
Licence No: LIC-BETA-2002
Issued Date: 2026/11/05
Expiration Date: 5 November 2028
TIN: TAX-BETA-3002""",
        expected={
            "company_name": "Beta Imaginary Services PLC",
            "registration_number": "REG-BETA-1002",
            "license_number": "LIC-BETA-2002",
            "issue_date": "2026-11-05",
            "expiry_date": "2028-11-05",
            "tax_identifier": "TAX-BETA-3002",
        },
        requires_ocr=False,
        format="digital_pdf",
    ),
    FictionalQualityDocument(
        name="gamma_tax_scan",
        filename="gamma-tax-certificate.png",
        mime_type="image/png",
        source_text="""Company Name: Gamma Fictional Foods Ltd
Registration Number: REG-GAMMA-1003
License Number: LIC-GAMMA-2003
Issue Date: 2026-12-01
Expiry Date: 2029-12-01
Tax ID: TAX-GAMMA-3003""",
        expected={
            "company_name": "Gamma Fictional Foods Ltd",
            "registration_number": "REG-GAMMA-1003",
            "license_number": "LIC-GAMMA-2003",
            "issue_date": "2026-12-01",
            "expiry_date": "2029-12-01",
            "tax_identifier": "TAX-GAMMA-3003",
        },
        requires_ocr=True,
        format="scanned_png",
    ),
    FictionalQualityDocument(
        name="delta_license_scan",
        filename="delta-license-scan.pdf",
        mime_type="application/pdf",
        source_text="""Company Name: Delta Imaginary Textiles Ltd
Registration Number: REG-DELTA-1004
Trade License Number: LIC-DELTA-2004
Issue Date: December 2, 2026
Expires Date: December 2, 2029
Tax Identifier: TAX-DELTA-3004""",
        expected={
            "company_name": "Delta Imaginary Textiles Ltd",
            "registration_number": "REG-DELTA-1004",
            "license_number": "LIC-DELTA-2004",
            "issue_date": "2026-12-02",
            "expiry_date": "2029-12-02",
            "tax_identifier": "TAX-DELTA-3004",
        },
        requires_ocr=True,
        format="scanned_pdf",
    ),
)


def digital_pdf_bytes(text: str) -> bytes:
    pdf = pymupdf.open()
    page = pdf.new_page(width=595, height=842)
    y_position = 90
    for line in text.splitlines():
        page.insert_text((72, y_position), line, fontsize=12)
        y_position += 30
    content = pdf.tobytes()
    pdf.close()
    return content


def scanned_png_bytes(text: str) -> bytes:
    image = Image.new("RGB", (1800, 900), "white")
    draw = ImageDraw.Draw(image)
    font = _quality_font()
    draw.multiline_text((80, 80), text, fill="black", font=font, spacing=28)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def document_bytes(document: FictionalQualityDocument) -> bytes:
    if document.format == "digital_pdf":
        return digital_pdf_bytes(document.source_text)
    image_bytes = scanned_png_bytes(document.source_text)
    if document.format == "scanned_png":
        return image_bytes
    image_pdf = pymupdf.open(stream=image_bytes, filetype="png")
    pdf_bytes = image_pdf.convert_to_pdf()
    image_pdf.close()
    return pdf_bytes


def _quality_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, 38)
        except OSError:
            continue
    return ImageFont.load_default()
