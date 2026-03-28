import os
import base64
from pathlib import Path
from PROMPT import PROMPT
import fitz  # PyMuPDF
from anthropic import Anthropic
from dotenv import load_dotenv

PDF_PATH = r"C:\Users\User\Documents\catalogue_parser\catalogues\2026 outdoor catalog 18-3.pdf"  # change this


# --- Load API key ---
load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# --- Extract text from PDF page ---
def extract_text_from_pdf(pdf_path: str, page_num: int) -> str:
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    return page.get_text()


# --- (Optional) Extract image of page ---
def extract_image_from_pdf(pdf_path: str, page_num: int) -> bytes:
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap()
    return pix.tobytes("png")


# --- Send to Claude ---
def extract_with_claude(text: str = None, image_bytes: bytes = None):
    content = []

    if text:
        content.append({
            "type": "text",
            "text": f"""
Extract all products from this catalogue page.

Return JSON list with:
- name
- sku (if available)
- price (if available)

Text:
{text}
"""
        })

    if image_bytes:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            },
        })

    response = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=1000,
        temperature=0,
        messages=[
            {"role": "user", "content": content}
        ],
    )

    return response.content[0].text


# --- Main test runner ---
def run_single_page(pdf_path: str, page_num: int, use_image=False):
    print(f"\n📄 Processing page {page_num}...\n")

    if use_image:
        img = extract_image_from_pdf(pdf_path, page_num)
        result = extract_with_claude(image_bytes=img)
    else:
        text = extract_text_from_pdf(pdf_path, page_num)
        result = extract_with_claude(text=text)

    print("✅ Result:\n")
    print(result)


# --- CLI entry ---
if __name__ == "__main__":
    PAGE_NUM = 0                      # change page here
    USE_IMAGE = False                # toggle this

    run_single_page(PDF_PATH, PAGE_NUM, USE_IMAGE)