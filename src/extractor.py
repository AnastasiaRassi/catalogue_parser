import anthropic
import json
from pathlib import Path
import time
from dotenv import load_dotenv
import os
from typing import Dict, Any
from utils.extractor_utils import extract_catalogue_page

load_dotenv()
API_KEY = anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def process_catalogue(
    images_dir: str,
    output_file: str,
    skip_first: int = 3,
    start_page: int = 1,
    end_page: int = None,
    model: str = "claude-sonnet-3-5-20241022",
    delay: float = 0.5
) -> Dict[str, Any]:
    """
    Process entire catalogue directory.
    
    Args:
        images_dir: Directory containing catalogue images
        output_file: JSON file to save results
        skip_first: Number of initial images to skip
        start_page: Page number to start processing (1-indexed)
        end_page: Page number to end processing (None = all)
        model: Claude model to use
        delay: Delay between API calls in seconds
        
    Returns:
        Dictionary with processing summary
    """
    client = anthropic.Anthropic(api_key=API_KEY)
    images_path = Path(images_dir)
    
    # Get all image files, sorted
    image_files = sorted([
        f for f in images_path.glob("*")
        if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ])
    
    print(f"Found {len(image_files)} image files")
    print(f"Skipping first {skip_first} images")
    
    # Skip first N images
    image_files = image_files[skip_first:]
    
    # Apply page range if specified
    if end_page:
        image_files = image_files[start_page-1:end_page]
    else:
        image_files = image_files[start_page-1:]
    
    print(f"Processing {len(image_files)} images (pages {start_page} to {start_page + len(image_files) - 1})")
    
    all_results = []
    all_products = []
    failed_pages = []
    
    for idx, image_file in enumerate(image_files):
        page_num = start_page + idx
        print(f"\nProcessing page {page_num}: {image_file.name}...")
        
        result = extract_catalogue_page(client, image_file, page_num, model)
        all_results.append(result)
        
        if result["success"]:
            all_products.extend(result["products"])
            print(f"  ✓ Extracted {len(result['products'])} products")
        else:
            failed_pages.append(page_num)
            print(f"  ✗ Failed: {result['error']}")
        
        # Rate limiting - be nice to the API
        if idx < len(image_files) - 1:  # Don't delay after last image
            time.sleep(delay)
    
    # Save results
    output_data = {
        "summary": {
            "total_pages": len(image_files),
            "successful_pages": len([r for r in all_results if r["success"]]),
            "failed_pages": failed_pages,
            "total_products": len(all_products)
        },
        "products": all_products,
        "detailed_results": all_results
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total pages processed: {len(image_files)}")
    print(f"Successful: {output_data['summary']['successful_pages']}")
    print(f"Failed: {len(failed_pages)}")
    print(f"Total products extracted: {len(all_products)}")
    print(f"Results saved to: {output_file}")
    
    if failed_pages:
        print(f"\nFailed pages: {failed_pages}")
    
    return output_data


if __name__ == "__main__":
    # TEST MODE - Process only 4 images
    TEST_MODE = True
    
    if TEST_MODE:
        print("=" * 60)
        print("RUNNING IN TEST MODE (4 images only)")
        print("=" * 60)
        
        result = process_catalogue(
            images_dir="catalogue_images",  # Your directory with extracted PDF images
            output_file="catalogue_test_output.json",
            skip_first=3,  # Skip first 3 images (cover, intro, etc.)
            start_page=1,
            end_page=4,  # Only process 4 pages for testing
            model="claude-sonnet-3-5-20241022",
            delay=1.0  # 1 second delay between calls
        )
    else:
        # FULL RUN - Process all 285 images
        print("=" * 60)
        print("RUNNING FULL EXTRACTION (all images)")
        print("=" * 60)
        
        result = process_catalogue(
            images_dir="catalogue_images",
            output_file="catalogue_full_output.json",
            skip_first=3,
            start_page=1,
            end_page=None,  # Process all
            model="claude-sonnet-3-5-20241022",
            delay=0.5
        )