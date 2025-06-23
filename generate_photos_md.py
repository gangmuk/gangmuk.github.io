import os
import sys
import yaml
from pathlib import Path
from PIL import Image, ImageOps
import io
from object_detection import detect_object
from image_description import describe_image
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_sentiment(filename):
    """Generate a cute sentiment/description for the photo"""
    # Simple placeholder - you can make this more sophisticated later
    sentiments = [
        "What a magical moment! ✨",
        "This brings back wonderful memories 💭",
        "Adventure awaits around every corner 🌟",
        "Life is beautiful in all its forms 🌸",
        "Capturing the essence of wanderlust 🗺️",
        "A picture worth a thousand stories 📚",
        "Finding beauty in everyday moments ☀️",
        "Travel feeds the soul 🌍"
    ]
    return sentiments[hash(filename) % len(sentiments)]

def parse_location(filename):
    if ',' in filename:
        city = filename.split(',')[0].strip()
        country = filename.split(',')[1].strip()
        return city, country
    return "Unknown", "Unknown"

def cleanup_orphaned_optimized_files(photos_dir, optimized_dir):
    """Remove optimized files that no longer have corresponding originals"""
    logger.info(f"\nCleaning up orphaned files in {optimized_dir}")
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.PNG'}
    cleaned_count = 0
    
    for optimized_file in optimized_dir.glob("*_optimized.*"):
        # Extract original filename by removing '_optimized' suffix
        original_stem = optimized_file.stem.replace('_optimized', '')
        
        # Check if any original file with this stem exists
        original_exists = any(
            (photos_dir / f"{original_stem}{ext}").exists() 
            for ext in image_extensions
        )
        
        if not original_exists:
            logger.info(f"  Removing orphaned file: {optimized_file.name}")
            optimized_file.unlink()
            cleaned_count += 1
    
    logger.info(f"Cleaned up {cleaned_count} orphaned files")

def optimize_image(image_path, max_size_kb):
    """Optimize image by resizing and compressing until it's under max_size_kb"""
    logger.info(f"\nProcessing {image_path.name}:")
    
    # Open image and apply EXIF orientation to prevent rotation issues
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)  # This fixes rotation issues
    
    # Convert RGBA to RGB if necessary
    if img.mode in ('RGBA', 'LA'):
        logger.info(f"  Converting {img.mode} to RGB")
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background

    # Calculate initial size
    temp_buffer = io.BytesIO()
    img.save(temp_buffer, format='JPEG', quality=85)
    current_size = len(temp_buffer.getvalue()) / 1024  # Size in KB
    logger.info(f"  Original size: {current_size:.2f}KB")

    # If image is already small enough, just return optimized version
    if current_size <= max_size_kb:
        logger.info(f"  Image is already under {max_size_kb}KB, skipping optimization")
        return img

    # Calculate new dimensions while maintaining exact aspect ratio
    original_width, original_height = img.size
    aspect_ratio = original_width / original_height
    
    # Start with a reasonable max dimension and scale down if needed
    max_dimension = 1200
    
    if original_width > original_height:
        new_width = min(max_dimension, original_width)
        new_height = int(new_width / aspect_ratio)
    else:
        new_height = min(max_dimension, original_height)
        new_width = int(new_height * aspect_ratio)
    
    logger.info(f"  Original dimensions: {original_width}x{original_height}")
    logger.info(f"  New dimensions: {new_width}x{new_height}")
    logger.info(f"  Aspect ratio preserved: {aspect_ratio:.3f}")
    
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Compress with decreasing quality until size is under max_size_kb
    quality = 85
    while quality > 20:
        temp_buffer = io.BytesIO()
        img.save(temp_buffer, format='JPEG', quality=quality)
        current_size = len(temp_buffer.getvalue()) / 1024
        logger.info(f"  Quality {quality}: {current_size:.2f}KB")
        
        if current_size <= max_size_kb:
            break
            
        quality -= 5

    logger.info(f"  Final size: {current_size:.2f}KB")
    return img

def generate_photos_md(max_size_kb):
    # Path to your photos directory and optimized photos directory
    photos_dir = Path("assets/img/photos")
    optimized_dir = Path("assets/img/photos_optimized")
    logger.info(f"\nCreating optimized directory: {optimized_dir}")
    optimized_dir.mkdir(exist_ok=True)

    cleanup_orphaned_optimized_files(photos_dir, optimized_dir)
    
    
    # Load existing photos.md to check for existing objects data
    existing_items = {}
    if os.path.exists('photos.md'):
        try:
            with open('photos.md', 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract YAML front matter
                if content.startswith('---'):
                    yaml_end = content.find('---', 3)
                    if yaml_end != -1:
                        yaml_content = content[3:yaml_end]
                        existing_data = yaml.safe_load(yaml_content)
                        if existing_data and 'items' in existing_data:
                            # Create a lookup dict by title for quick access
                            for item in existing_data['items']:
                                existing_items[item.get('title', '')] = item
                            logger.info(f"Loaded {len(existing_items)} existing items from photos.md")
        except Exception as e:
            logger.info(f"Could not load existing photos.md: {e}")
    
    # List to store photo items
    items = []
    
    # Valid image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.PNG'}
    
    # Process each image
    total_files = len([f for f in photos_dir.iterdir() if f.suffix.lower() in image_extensions])
    logger.info(f"\nFound {total_files} images to process")
    
    processed = 0
    for photo_file in photos_dir.iterdir():
        if photo_file.suffix.lower() in image_extensions:
            processed += 1
            # optimized_path = optimized_dir / f"{photo_file.stem}_optimized.jpg"
            optimized_path = optimized_dir / f"{photo_file.stem}{photo_file.suffix}"
            
            # Optimize image if not already optimized
            if not optimized_path.exists():
                logger.info(f"Original input photo: {processed}/{total_files}, output: {optimized_path}")
                try:
                    optimized_img = optimize_image(photo_file, max_size_kb)
                    optimized_img.save(optimized_path, 'JPEG', quality=85)
                    logger.info(f"Saved optimized image to: {optimized_path}")
                except Exception as e:
                    logger.info(f"Error processing {photo_file}: {e}")
                    continue
            else:
                logger.info(f"Optimized version already exists, skipping for {optimized_path}")

            # Create item entry with optimized image path
            city, country = parse_location(photo_file.stem)
            sentiment = generate_sentiment(photo_file.stem)
            
            
            photo_title = photo_file.stem.replace('-', ' ').replace('_', ' ')
            existing_item = existing_items.get(photo_title, {})
            
            if 'objects' in existing_item and existing_item['objects']:
                logger.info(f"Objects field already exists for {photo_file.name}, skipping detection")
                objects_str = existing_item['objects']
            else:
                logger.info(f"Running object detection for {photo_file.name}")
                objects = detect_object(photo_file, 'l', 640)
                objects_str = ",".join(objects) if objects else "None"
                print(f"Detected objects: {objects_str}")

            logger.info(f"{photo_file.name}\n - City: {city}, Country: {country}")
            item = {
                'title': photo_file.stem.replace('-', ' ').replace('_', ' '),
                'image': {
                    'src': f"/assets/img/photos_optimized/{optimized_path.name}",
                    'alt': photo_file.stem.replace('-', ' ').replace('_', ' ')
                },
                'city': city,
                'country': country,
                'sentiment': sentiment,
                'objects': objects_str,
                # 'description': description,
            }
            items.append(item)

    logger.info(f"\nGenerating photos.md with {len(items)} items")
    # Create front matter
    front_matter = {
        'layout': 'photos',
        'title': 'Life',
        'slug': '/photos',
        'items': items
    }

    # Generate the photos.md content
    content = "---\n"
    content += yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)
    content += "---\n"

    # Write to photos.md
    with open('photos.md', 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info("\nFinished! photos.md has been updated.")

if __name__ == "__main__":
    max_size_kb = sys.argv[1] if len(sys.argv) > 1 else 500
    logger.info(f"Max size for optimized images: {max_size_kb}KB")
    generate_photos_md(max_size_kb)
    logger.info(f"Optimization done! Max size for optimized images: {max_size_kb}KB")
    