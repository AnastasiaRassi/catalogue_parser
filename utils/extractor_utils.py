import base64
import json
from anthropic import Anthropic
import anthropic
from pathlib import Path
from typing import Dict, Any
from src.prompt import PROMPT


# def encode_image(image_path: Path) -> str:
#     """Encode image to base64 string."""
#     with open(image_path, "rb") as image_file:
#         return base64.standard_b64encode(image_file.read()).decode("utf-8")

from PIL import Image
import io


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
            print(f"  Compressed from {len(original_data)/1024/1024:.1f}MB to {len(compressed_data)/1024/1024:.1f}MB (quality={quality})")
            return base64.standard_b64encode(compressed_data).decode("utf-8"), "image/jpeg"  # ← Changed!
    
    # If still too large, resize
    img.thumbnail((2000, 2000))
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=45, optimize=True)
    compressed_data = buffer.getvalue()
    print(f"  Resized and compressed to {len(compressed_data)/1024/1024:.1f}MB")
    return base64.standard_b64encode(compressed_data).decode("utf-8"), "image/jpeg"  # ← Changed!


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


def extract_catalogue_page(
    client: anthropic.Anthropic,
    image_path: Path,
    page_number: int,
    model: str = "claude-sonnet-3-5-20241022"
) -> Dict[str, Any]:
    """
    Extract product data from a single catalogue page.
    
    Args:
        client: Anthropic client instance
        image_path: Path to the image file
        page_number: Page number for tracking
        model: Claude model to use
        
    Returns:
        Dictionary with extraction results
    """
    try:
        # Encode image
        image_data, media_type = compress_image_if_needed(image_path)

        # Create message with image
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"{PROMPT}{page_number}"
                        }
                    ],
                }
            ],
        )
        
        # Extract text response
        response_text = message.content[0].text
        
        # Try to parse JSON from response
        # Remove markdown code blocks if present
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]  # Remove ```json
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]  # Remove ```
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]  # Remove ```
        cleaned_response = cleaned_response.strip()
        
        # Parse JSON
        products = json.loads(cleaned_response)
        
        return {
            "success": True,
            "page": page_number,
            "image_path": str(image_path),
            "products": products,
            "raw_response": response_text,
            "error": None
        }
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "page": page_number,
            "image_path": str(image_path),
            "products": [],
            "raw_response": message.content[0].text if 'message' in locals() else None,
            "error": f"JSON parsing error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "page": page_number,
            "image_path": str(image_path),
            "products": [],
            "raw_response": None,
            "error": f"Extraction error: {str(e)}"
        }

