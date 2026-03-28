import fitz  # PyMuPDF
from pathlib import Path


def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 300):
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)

    zoom = dpi / 72  # 72 is default PDF DPI
    matrix = fitz.Matrix(zoom, zoom)

    print(f"📄 Converting {len(doc)} pages...")

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=matrix)

        output_file = output_dir / f"page_{page_num + 1:03d}.png"  # Zero-pad to 3 digits
        pix.save(output_file)

        print(f"✅ Saved: {output_file}")

    print("\n🎉 Done!")


# --- CLI usage ---
if __name__ == "__main__":
    PDF_PATH = r"C:\Users\User\Documents\catalogue_parser\catalogues\2026 outdoor catalog 18-3.pdf"
    OUTPUT_DIR = r"C:\Users\User\Documents\catalogue_parser\catalogues\images"

    DPI = 300  # 200–300 recommended

    pdf_to_images(PDF_PATH, OUTPUT_DIR, DPI)