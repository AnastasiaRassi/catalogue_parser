import anthropic
import json
from pathlib import Path
import time
from dotenv import load_dotenv
import os
from typing import Dict, Any, List
from utils.extractor_utils import extract_catalogue_page_batch
from anthropic import Anthropic

model = "claude-haiku-4-5"
# model = "claude-sonnet-4-6"


load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY") 


def process_catalogue(
    images_dir: str,
    output_file: str,
    skip_first: int,
    start_page: int = 1,
    end_page: int = None,
    model: str = model,
    delay: float = 0.5,
    batch_size: int = 2
) -> Dict[str, Any]:
    """
    Process entire catalogue directory with batching support.
    
    Args:
        images_dir: Directory containing catalogue images
        output_file: JSON file to save results
        skip_first: Number of initial images to skip
        start_page: Page number to start processing (1-indexed)
        end_page: Page number to end processing (None = all)
        model: Claude model to use
        delay: Delay between API calls in seconds
        batch_size: Number of images to process per API call (1 = no batching)
        
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
    start_idx = start_page - 1
    if end_page is not None:
        image_files = image_files[start_idx:end_page]
    else:
        image_files = image_files[start_idx:]
    
    print(f"Processing {len(image_files)} images in batches of {batch_size}")
    print(f"Pages {start_page} to {start_page + len(image_files) - 1}")
    
    # Progress file for crash recovery
    progress_file = output_file.replace('.json', '_progress.json').replace('.txt', '_progress.json')
    
    # Load existing progress if it exists
    if Path(progress_file).exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)
            all_results = checkpoint.get('detailed_results', [])
            all_products = checkpoint.get('products', [])
            completed_pages = {r['page'] for r in all_results if r.get('success')}
            print(f"Resuming from checkpoint: {len(completed_pages)} pages already completed")
    else:
        all_results = []
        all_products = []
        completed_pages = set()
    
    failed_pages = []
    
    # Process in batches
    for batch_start_idx in range(0, len(image_files), batch_size):
        batch_end_idx = min(batch_start_idx + batch_size, len(image_files))
        batch_files = image_files[batch_start_idx:batch_end_idx]
        batch_page_numbers = [start_page + batch_start_idx + i for i in range(len(batch_files))]
        
        # Skip if all pages in batch already completed
        if all(page_num in completed_pages for page_num in batch_page_numbers):
            print(f"\nSkipping batch pages {batch_page_numbers[0]}-{batch_page_numbers[-1]} (already completed)")
            continue
        
        print(f"\n{'='*60}")
        if len(batch_files) > 1:
            print(f"Processing batch: pages {batch_page_numbers[0]}-{batch_page_numbers[-1]}")
        else:
            print(f"Processing page {batch_page_numbers[0]}")
        print(f"Files: {[f.name for f in batch_files]}")
        print(f"{'='*60}")
        
        # Extract batch
        batch_results = extract_catalogue_page_batch(
            client, 
            batch_files, 
            batch_page_numbers, 
            model
        )
        
        # Process results
        for result in batch_results:
            all_results.append(result)
            
            if result["success"]:
                all_products.extend(result["products"])
                print(f"  ✓ Page {result['page']}: Extracted {len(result['products'])} products")
            else:
                failed_pages.append(result['page'])
                print(f"  ✗ Page {result['page']}: Failed - {result['error']}")
        
        # Save progress after each batch
        checkpoint_data = {
            'products': all_products,
            'detailed_results': all_results
        }
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        # Rate limiting between batches
        if batch_end_idx < len(image_files):
            time.sleep(delay)
    
    # Save final results
    output_data = {
        "summary": {
            "total_pages": len(image_files),
            "successful_pages": len([r for r in all_results if r.get("success")]),
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
    # TEST MODE - Process only a few images to verify quality
    TEST_MODE = True
    
    if TEST_MODE:
        print("=" * 60)
        print("RUNNING IN TEST MODE")
        print("=" * 60)
        
        result = process_catalogue(
            images_dir=r"C:\Users\User\Documents\catalogue_parser\catalogues\images", 
            output_file=r"C:\Users\User\Documents\catalogue_parser\data\testing\testing.json",
            skip_first=0,  # Skip cover pages
            start_page=117,
            end_page=118,  # Test first 10 catalogue pages
            model=model,
            delay=1.0,
            batch_size=2  # Process 2 images per API call
        )
    else:
        # FULL RUN - Process all images
        print("=" * 60)
        print("RUNNING FULL EXTRACTION")
        print("=" * 60)
        
        result = process_catalogue(
            images_dir=r"C:\Users\User\Documents\catalogue_parser\catalogues\images",
            output_file=r"C:\Users\User\Documents\catalogue_parser\data\full_results.json",
            skip_first=3,  # Skip first 3 pages (cover, intro, etc.)
            start_page=1,
            end_page=287,  # 291 total - 3 skip - 1 last page = 287
            model=model,
            delay=0.5,
            batch_size=2  # Batch 2 images per call for speed
        )
