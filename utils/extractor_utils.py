import anthropic
import base64
import json
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image
import io
from src.prompt import PROMPT


def get_image_media_type(image_path: Path) -> str:
    extension = image_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(extension, "image/jpeg")


def compress_image_if_needed(image_path: Path, max_size_mb: float = 3.5) -> tuple[str, str]:
    max_bytes = int(max_size_mb * 1024 * 1024)

    with open(image_path, "rb") as f:
        original_data = f.read()

    img = Image.open(image_path)

    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")

    for quality in [85, 75, 65, 55, 45]:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        compressed_data = buffer.getvalue()

        if len(compressed_data) <= max_bytes:
            print(
                f"  Compressed {image_path.name}: "
                f"{len(original_data)/1024/1024:.1f}MB → {len(compressed_data)/1024/1024:.1f}MB "
                f"(quality={quality})"
            )
            return base64.b64encode(compressed_data).decode("utf-8"), "image/jpeg"

    img.thumbnail((2000, 2000))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=45, optimize=True)
    compressed_data = buffer.getvalue()
    print(f"  Resized {image_path.name}: {len(compressed_data)/1024/1024:.1f}MB")
    return base64.b64encode(compressed_data).decode("utf-8"), "image/jpeg"


def _clean_json_response(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def extract_catalogue_page_batch(
    client: anthropic.Anthropic,
    image_paths: List[Path],
    page_numbers: List[int],
    model: str
) -> List[Dict[str, Any]]:
    """
    Extract product data from multiple catalogue pages in one API call.

    Important:
    - The page numbers passed in are the source of truth.
    - Model-returned page values are not trusted for routing.
    """
    response_text = ""
    try:
        content = []

        for image_path, page_num in zip(image_paths, page_numbers):
            image_data, media_type = compress_image_if_needed(image_path)

            content.append({
                "type": "text",
                "text": f"PAGE {page_num}: extract products from this image only."
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            })

        prompt_text = f"""
{PROMPT}

You are processing {len(page_numbers)} pages: {page_numbers}.

Return ONLY valid JSON in this exact format:
[
  {{
    "page": {page_numbers[0]},
    "products": [ ... ]
  }}
]

Rules:
- Return exactly {len(page_numbers)} page objects, in the same order as the input images.
- Do not merge pages.
- Do not invent page numbers.
- Use the provided page number for each page object.
- Inside each page object, include all products found on that page.
- If a page has no products, return an empty products array for that page.
"""

        content.append({
            "type": "text",
            "text": prompt_text
        })

        message = client.messages.create(
            model=model,
            max_tokens=8192,
            messages=[{"role": "user", "content": content}]
        )

        response_text = message.content[0].text
        cleaned_response = _clean_json_response(response_text)
        parsed = json.loads(cleaned_response)

        results: List[Dict[str, Any]] = []

        # Preferred format: [{page: X, products:[...]} , ...]
        if isinstance(parsed, list) and (len(parsed) == 0 or (isinstance(parsed[0], dict) and "products" in parsed[0])):
            for idx, (image_path, expected_page) in enumerate(zip(image_paths, page_numbers)):
                block = parsed[idx] if idx < len(parsed) and isinstance(parsed[idx], dict) else {}
                raw_products = block.get("products", []) if isinstance(block, dict) else []

                normalized_products = []
                if isinstance(raw_products, list):
                    for product in raw_products:
                        if isinstance(product, dict):
                            product["page"] = expected_page
                            normalized_products.append(product)

                results.append({
                    "success": True,
                    "page": expected_page,
                    "image_path": str(image_path),
                    "products": normalized_products,
                    "raw_response": response_text if idx == 0 else None,
                    "error": None
                })

            return results

        # Fallback format: flat array of products
        products_by_page = {p: [] for p in page_numbers}

        if isinstance(parsed, list):
            for product in parsed:
                if not isinstance(product, dict):
                    continue

                # Trust caller page numbers over model page numbers
                model_page = product.get("page")
                if model_page in products_by_page:
                    page_key = model_page
                else:
                    # keep data instead of dropping it
                    page_key = page_numbers[0]

                product["page"] = page_key
                products_by_page.setdefault(page_key, []).append(product)

        for idx, (image_path, expected_page) in enumerate(zip(image_paths, page_numbers)):
            results.append({
                "success": True,
                "page": expected_page,
                "image_path": str(image_path),
                "products": products_by_page.get(expected_page, []),
                "raw_response": response_text if idx == 0 else None,
                "error": None
            })

        return results

    except json.JSONDecodeError as e:
        return [{
            "success": False,
            "page": page_num,
            "image_path": str(image_path),
            "products": [],
            "raw_response": response_text if response_text else None,
            "error": f"JSON parsing error: {str(e)}"
        } for image_path, page_num in zip(image_paths, page_numbers)]

    except Exception as e:
        return [{
            "success": False,
            "page": page_num,
            "image_path": str(image_path),
            "products": [],
            "raw_response": response_text if response_text else None,
            "error": f"Extraction error: {str(e)}"
        } for image_path, page_num in zip(image_paths, page_numbers)]