from pathlib import Path
from PIL import Image
import io

def check_all_images(images_dir: str, skip_first: int = 3, max_size_mb: float = 4.0):
    """
    Check all images and identify which ones will need compression.
    """
    images_path = Path(images_dir)
    max_bytes = int(max_size_mb * 1024 * 1024)
    
    # Get all image files, sorted
    image_files = sorted([
        f for f in images_path.glob("*")
        if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ])
    
    print(f"Found {len(image_files)} total images")
    print(f"Checking {len(image_files) - skip_first} images (skipping first {skip_first})")
    print(f"Max allowed size: {max_size_mb}MB")
    print("="*80)
    
    # Skip first N
    image_files = image_files[skip_first:]
    
    oversized = []
    failed_compression = []
    total_original_size = 0
    total_compressed_size = 0
    
    for idx, img_path in enumerate(image_files, start=1):
        # Read original
        with open(img_path, "rb") as f:
            original_data = f.read()
        
        original_size_mb = len(original_data) / 1024 / 1024
        total_original_size += original_size_mb
        
        if len(original_data) <= max_bytes:
            # Already small enough
            total_compressed_size += original_size_mb
            continue
        
        # Try to compress
        oversized.append((idx, img_path.name, original_size_mb))
        
        try:
            img = Image.open(img_path)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            compressed = False
            # Try quality levels
            for quality in [75, 65, 55, 45, 35]:
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                compressed_data = buffer.getvalue()
                
                if len(compressed_data) <= max_bytes:
                    compressed_size_mb = len(compressed_data) / 1024 / 1024
                    total_compressed_size += compressed_size_mb
                    print(f"Page {idx:3d} | {img_path.name:20s} | {original_size_mb:5.1f}MB → {compressed_size_mb:5.1f}MB (Q={quality})")
                    compressed = True
                    break
            
            if not compressed:
                # Try resize
                img.thumbnail((2000, 2000))
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=35, optimize=True)
                compressed_data = buffer.getvalue()
                
                if len(compressed_data) <= max_bytes:
                    compressed_size_mb = len(compressed_data) / 1024 / 1024
                    total_compressed_size += compressed_size_mb
                    print(f"Page {idx:3d} | {img_path.name:20s} | {original_size_mb:5.1f}MB → {compressed_size_mb:5.1f}MB (RESIZED)")
                else:
                    failed_compression.append((idx, img_path.name, original_size_mb, len(compressed_data)/1024/1024))
                    print(f"⚠️  Page {idx:3d} | {img_path.name:20s} | {original_size_mb:5.1f}MB → {len(compressed_data)/1024/1024:5.1f}MB (STILL TOO LARGE!)")
        
        except Exception as e:
            failed_compression.append((idx, img_path.name, original_size_mb, str(e)))
            print(f"❌ Page {idx:3d} | {img_path.name:20s} | ERROR: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total images checked: {len(image_files)}")
    print(f"Images requiring compression: {len(oversized)}")
    print(f"Images that FAILED compression: {len(failed_compression)}")
    print(f"Total original size: {total_original_size:.1f}MB")
    print(f"Total compressed size: {total_compressed_size:.1f}MB")
    print(f"Compression ratio: {(1 - total_compressed_size/total_original_size)*100:.1f}% reduction")
    
    if failed_compression:
        print("\n" + "="*80)
        print("⚠️  FAILED COMPRESSIONS - THESE PAGES WILL FAIL!")
        print("="*80)
        for idx, name, orig_size, result in failed_compression:
            if isinstance(result, str):
                print(f"Page {idx:3d} | {name} | Error: {result}")
            else:
                print(f"Page {idx:3d} | {name} | {orig_size:.1f}MB → {result:.1f}MB (still exceeds {max_size_mb}MB)")
        
        print("\n🔧 SOLUTIONS:")
        print("1. Lower max_size_mb to 3.5MB in compress_image_if_needed()")
        print("2. Add more aggressive resize: img.thumbnail((1600, 1600))")
        print("3. Manually compress these specific images before processing")
    else:
        print("\n✅ ALL IMAGES CAN BE COMPRESSED SUCCESSFULLY!")
        print("Safe to proceed with full extraction.")
    
    return failed_compression


if __name__ == "__main__":
    failed = check_all_images(
        images_dir=r"C:\Users\User\Documents\catalogue_parser\catalogues\images",
        skip_first=3,
        max_size_mb=4.0
    )
    
    if failed:
        print(f"\n❌ {len(failed)} images will fail. Fix these before running extraction.")
    else:
        print("\n✅ All clear! Ready for full extraction.")