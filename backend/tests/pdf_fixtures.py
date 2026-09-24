import io
import pypdf

def make_test_pdf_bytes(page_count: int = 1, text: str = None) -> bytes:
    """Generate structurally valid PDF bytes with the specified number of pages and optional embedded text."""
    writer = pypdf.PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=100, height=100)
    if text:
        writer.add_metadata({"/Title": text})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
