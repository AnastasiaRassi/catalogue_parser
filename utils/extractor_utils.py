import anthropic
import base64
import json
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image
import io
from src.prompt import PROMPT


def get_image_media_type(image_path: Path) -> str:
    """Determine media type from file extension."""
    extension = image_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    return media_types.get(extension, "image/jpeg")


def compress_image_if_needed(image_path: Path, max_size_mb: float = 4.5) -> tuple[str, str]:
    """Compress image if needed. Returns (base64_data, media_type)."""
    max_bytes = int(max_size_mb * 1024 * 1024)
    
    # Read original file
    with open(image_path, "rb") as f:
        original_data = f.read()
    
    original_media_type = get_image_media_type(image_path)
    
    # If under limit, return as-is
    if len(original_data) <= max_bytes:
        return base64.standard_b64encode(original_data).decode("utf-8"), original_media_type
    
    # Compress image
    img = Image.open(image_path)
    
    # Convert to RGB if needed
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    
    # Try progressively lower quality
    for quality in [85, 75, 65, 55, 45]:
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        compressed_data = buffer.getvalue()
        
        if len(compressed_data) <= max_bytes:
            print(f"  Compressed {image_path.name}: {len(original_data)/1024/1024:.1f}MB → {len(compressed_data)/1024/1024:.1f}MB (quality={quality})")
            return base64.standard_b64encode(compressed_data).decode("utf-8"), "image/jpeg"
    
    # If still too large, resize
    img.thumbnail((2000, 2000))
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=45, optimize=True)
    compressed_data = buffer.getvalue()
    print(f"  Resized {image_path.name}: {len(compressed_data)/1024/1024:.1f}MB")
    return base64.standard_b64encode(compressed_data).decode("utf-8"), "image/jpeg"


def extract_catalogue_page_batch(
    client: anthropic.Anthropic,
    image_paths: List[Path],
    page_numbers: List[int],
    model: str
) -> List[Dict[str, Any]]:
    """
    Extract product data from multiple catalogue pages in one API call.
    
    Args:
        client: Anthropic client instance
        image_paths: List of paths to image files
        page_numbers: List of page numbers corresponding to images
        model: Claude model to use
        
    Returns:
        List of dictionaries with extraction results (one per page)
    """
    try:
        # Build content array with all images
        content = []
        
        for image_path, page_num in zip(image_paths, page_numbers):
            image_data, media_type = compress_image_if_needed(image_path)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            })
        
        # Add text prompt at the end
        page_range = f"{page_numbers[0]}-{page_numbers[-1]}" if len(page_numbers) > 1 else str(page_numbers[0])
        prompt_text = f"""{PROMPT}

These are pages {page_range}.
For each product, include the correct page number (one of: {page_numbers}).
Return a single JSON array containing products from ALL pages."""
        
        content.append({
            "type": "text",
            "text": prompt_text
        })
        
        # Create message
        message = client.messages.create(
            model=model,
            max_tokens=8192,  # Increased for multiple pages
            messages=[{
                "role": "user",
                "content": content
            }]
        )
        
        # Extract text response
        response_text = message.content[0].text
        
        # Parse JSON
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        all_products = json.loads(cleaned_response)
        
        # Group products by page
        products_by_page = {page_num: [] for page_num in page_numbers}
        for product in all_products:
            page = product.get('page')
            if page in products_by_page:
                products_by_page[page].append(product)
        
        # Create result for each page
        results = []
        for image_path, page_num in zip(image_paths, page_numbers):
            results.append({
                "success": True,
                "page": page_num,
                "image_path": str(image_path),
                "products": products_by_page[page_num],
                "raw_response": response_text if page_num == page_numbers[0] else None,  # Only store once
                "error": None
            })
        
        return results
        
    except json.JSONDecodeError as e:
        # If JSON parsing fails, mark all pages as failed
        return [{
            "success": False,
            "page": page_num,
            "image_path": str(image_path),
            "products": [],
            "raw_response": message.content[0].text if 'message' in locals() else None,
            "error": f"JSON parsing error: {str(e)}"
        } for image_path, page_num in zip(image_paths, page_numbers)]
        
    except Exception as e:
        # If extraction fails, mark all pages as failed
        return [{
            "success": False,
            "page": page_num,
            "image_path": str(image_path),
            "products": [],
            "raw_response": None,
            "error": f"Extraction error: {str(e)}"
        } for image_path, page_num in zip(image_paths, page_numbers)]