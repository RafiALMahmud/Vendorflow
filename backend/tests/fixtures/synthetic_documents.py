from io import BytesIO

import pymupdf
from PIL import Image, ImageDraw, ImageFont

FICTIONAL_DOCUMENT_TEXT = """Company Name: Northstar Fictional Trading Ltd
Registration Number: REG-FIC-2026-001
License Number: LIC-FIC-7788
Issue Date: 17 October 2026
Expiry Date: 2027-10-16
Tax Identifier: TAX-FIC-9900"""


def synthetic_digital_pdf_bytes() -> bytes:
    pdf = pymupdf.open()
    page = pdf.new_page(width=595, height=842)
    y_position = 90
    for line in FICTIONAL_DOCUMENT_TEXT.splitlines():
        page.insert_text((72, y_position), line, fontsize=12)
        y_position += 28
    content = pdf.tobytes()
    pdf.close()
    return content


def synthetic_scanned_image_bytes() -> bytes:
    image = Image.new("RGB", (1400, 700), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except OSError:
        font = ImageFont.load_default()
    draw.multiline_text((60, 60), FICTIONAL_DOCUMENT_TEXT, fill="black", font=font, spacing=24)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def synthetic_scanned_pdf_bytes() -> bytes:
    image_bytes = synthetic_scanned_image_bytes()
    image_pdf = pymupdf.open(stream=image_bytes, filetype="png")
    pdf_bytes = image_pdf.convert_to_pdf()
    image_pdf.close()
    return pdf_bytes
