import anthropic
import json
from pathlib import Path
import time
from dotenv import load_dotenv
import os
from typing import Dict, Any
from utils.extractor_utils import extract_catalogue_page
from anthropic import Anthropic
import anthropic

model = "claude-sonnet-4-6"

load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY") 

def process_catalogue(
    images_dir: str,
    output_file: str ,
    skip_first: int ,
    start_page: int = 1,
    end_page: int = None,
    model: str = model,
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
    
    # Apply page range if specified (FIXED)
    start_idx = start_page - 1

    if end_page is not None:
        image_files = image_files[start_idx:end_page]
    else:
        image_files = image_files[start_idx:]
    print(f"Processing {len(image_files)} images (pages {start_page} to {start_page + len(image_files) - 1})")
    
    progress_file = output_file.replace('.json', '_progress.json')
    
    # Load existing progress if it exists
    if Path(progress_file).exists():
        with open(progress_file, 'r') as f:
            checkpoint = json.load(f)
            all_results = checkpoint.get('detailed_results', [])
            all_products = checkpoint.get('products', [])
            completed_pages = {r['page'] for r in all_results if r['success']}
            print(f"Resuming from checkpoint: {len(completed_pages)} pages already completed")
    else:
        all_results = []
        all_products = []
        completed_pages = set()
    # END OF NEW LINES
    
    # Remove these old lines:
    # all_results = []
    # all_products = []
    failed_pages = []
    
    for idx, image_file in enumerate(image_files):
        page_num = start_page + idx
        
        # ADD THIS LINE:
        if page_num in completed_pages:
            print(f"Skipping page {page_num} (already completed)")
            continue
        
        print(f"\nProcessing page {page_num}: {image_file.name}...")
        
        result = extract_catalogue_page(client, image_file, page_num, model)
        all_results.append(result)
        
        if result["success"]:
            all_products.extend(result["products"])
            print(f"  ✓ Extracted {len(result['products'])} products")
        else:
            failed_pages.append(page_num)
            print(f"  ✗ Failed: {result['error']}")
        
        # ADD THESE LINES AFTER EACH PAGE:
        # Save progress after each page
        checkpoint_data = {
            'products': all_products,
            'detailed_results': all_results
        }
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        # END OF NEW LINES
        
        # Rate limiting
        if idx < len(image_files) - 1:
            time.sleep(delay)


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
        print("RUNNING IN TEST MODE (3 images only)")
        print("=" * 60)
        
        result = process_catalogue(
            images_dir=r"C:\Users\User\Documents\catalogue_parser\catalogues\images", 
            output_file=r"C:\Users\User\Documents\catalogue_parser\data\testing\testing.txt",
            skip_first=3,  # Skip first 3 images (cover, intro, etc.)
            start_page=1,
            end_page=5,  # Only process 4 pages for testing
            model = model,
            delay=1.0  # 1 second delay between calls
        )
    else:
        # FULL RUN - Process all 285 images
        print("=" * 60)
        print("RUNNING FULL EXTRACTION (all images)")
        print("=" * 60)
        

        
        BEGIN_AT = 3
        PAGES_AFTER_BEGIN = 287

        result = process_catalogue(
            images_dir=  r"C:\Users\User\Documents\catalogue_parser\catalogues\images",
            output_file =  r"C:\Users\User\Documents\catalogue_parser\data\json_results",
            skip_first=BEGIN_AT,
            start_page=1,
            end_page = PAGES_AFTER_BEGIN,  # Process all
            model = model,
            delay=0.5
        )
