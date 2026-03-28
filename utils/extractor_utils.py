import base64
import json
import anthropic
from pathlib import Path
from typing import Dict, Any
from prompt import PROMPT


def encode_image(image_path: Path) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.standard_b64encode(image_file.read()).decode("utf-8")


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
        image_data = encode_image(image_path)
        media_type = get_image_media_type(image_path)
        
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

