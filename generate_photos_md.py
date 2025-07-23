import os
import sys
import yaml
from pathlib import Path
from PIL import Image, ImageOps
import io
from object_detection import detect_object
from image_description import describe_image
from sentiment_analysis import analyze_single_image
from analyze_color import analyze_color_by_sections
from get_time_photo_taken import extract_timestamp

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_location(filename):
    if ',' in filename:
        city = filename.split(',')[0].strip()
        country = filename.split(',')[1].strip()
        return city, country
    return "Unknown", "Unknown"

def cleanup_orphaned_optimized_files(photos_base_dir, optimized_dir):
    """Remove optimized files that no longer have corresponding originals"""
    logger.info(f"\nCleaning up orphaned files in {optimized_dir}")
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.PNG'}
    cleaned_count = 0
    
    for optimized_file in optimized_dir.glob("*"):
        if optimized_file.is_file() and optimized_file.suffix.lower() in image_extensions:
            # For files without '_optimized' suffix, check if original exists
            original_stem = optimized_file.stem.replace('_optimized', '')
            
            # Check if any original file with this stem exists recursively
            original_exists = any(
                original_file.stem == original_stem
                for original_file in photos_base_dir.rglob("*")
                if original_file.is_file() and original_file.suffix.lower() in image_extensions
            )
            
            if not original_exists:
                logger.info(f"  Removing orphaned file: {optimized_file.name}")
                optimized_file.unlink()
                cleaned_count += 1
    
    logger.info(f"Cleaned up {cleaned_count} orphaned files")

def optimize_image(image_path, max_size_kb, max_dimension):
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

def update_photos_md(new_item):
    """Update photos.md by adding or updating an item"""
    logger.info(f"Updating photos.md with item: {new_item['title']}")
    
    # Load existing data
    existing_items = []
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
                            existing_items = existing_data['items']
        except Exception as e:
            logger.info(f"Could not load existing photos.md: {e}")
    
    # Find if item already exists and update it, or add new item
    item_found = False
    for i, existing_item in enumerate(existing_items):
        if existing_item.get('title') == new_item['title']:
            existing_items[i] = new_item  # Update existing item
            item_found = True
            logger.debug(f"Updated existing item: {new_item['title']}")
            break
    
    if not item_found:
        existing_items.append(new_item)  # Add new item
        logger.info(f"Added new item: {new_item['title']}")
    
    # Create front matter with updated items
    front_matter = {
        'layout': 'photos',
        'title': 'Life',
        'slug': '/photos',
        'items': existing_items
    }

    # Generate the photos.md content
    content = "---\n"
    content += yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)
    content += "---\n"

    # Write to photos.md
    with open('photos.md', 'w', encoding='utf-8') as f:
        f.write(content)

def generate_photos_md(max_size_kb, max_dimension, run_sentiment_analysis=False, run_color_analysis=False, run_object_detection=False, run_timestamp=False):
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
    
    # Find all image files recursively
    all_image_files = [
        f for f in photos_dir.rglob("*") 
        if f.is_file() and f.suffix.lower() in image_extensions
    ]
    
    total_files = len(all_image_files)
    logger.info(f"Found {total_files} images to process recursively")
    
    for processed, photo_file in enumerate(all_image_files, 1):
        print(f"photo_file: {photo_file}")
        original_dir = photo_file.parent
        print(f"original_dir: {original_dir}")
        exit()
        optimized_path = optimized_dir / f"{photo_file.stem}{photo_file.suffix}"
        
        logger.info(f"Processing {photo_file.name} from {photo_file.parent.name}/ ({processed}/{total_files})")
        
        # Optimize image if not already optimized
        if not optimized_path.exists():
            logger.info(f"Original input photo: {processed}/{total_files}, output: {optimized_path}")
            try:
                optimized_img = optimize_image(photo_file, max_size_kb, max_dimension)
                optimized_img.save(optimized_path, 'JPEG', quality=85)
                logger.info(f"Saved optimized image to: {optimized_path}")
            except Exception as e:
                logger.info(f"Error processing {photo_file}: {e}")
                continue
        else:
            logger.info(f"\tSkipping compression")
            
        city, country = parse_location(photo_file.stem)
        photo_title = photo_file.stem.replace('-', ' ').replace('_', ' ')
        existing_item = existing_items.get(photo_title, {})
        
        # Initialize variables
        sentiments_str = ""
        color_str = ""
        timestamp_str = ""
        objects_str = ""
        
        ########################
        ## Sentiment analysis ##
        ########################
        if run_sentiment_analysis:
            # Check if sentiment already exists
            if 'sentiment' in existing_item and existing_item.get('sentiment') and existing_item['sentiment'] != 'None':
                logger.info(f"- Skipping sentiment analysis, field already exists")
                sentiments_str = existing_item['sentiment']
            else:
                sentiment_list = analyze_single_image(photo_file, confidence_threshold=0.2)
                sentiments_str = ', '.join(sentiment_list) if sentiment_list else 'None'
                logger.info(f"- Analyzed sentiment: {sentiments_str}")
        else:
            sentiments_str = existing_item.get('sentiment', '')
            
        ####################
        ## Color analysis ##
        ####################
        if run_color_analysis:
            update_color_field = True
            if not update_color_field and 'color' in existing_item and existing_item.get('color') and existing_item['color'] != 'None':
                logger.info(f"- Skipping color analysis, field already exists")
                color_str = existing_item['color']
            else:
                try:
                    color_list = analyze_color_by_sections(photo_file)
                    color_str = ', '.join(color_list) if color_list else 'None'
                    logger.info(f"\tcolor: {color_str}")
                except Exception as e:
                    logger.info(f"Error analyzing color for {photo_file.name}: {e}")
                    color_str = 'None'
        else:
            color_str = existing_item.get('color', '')
        
        ###############
        ## Timestamp ##
        ###############
        if run_timestamp:
            if 'timestamp' in existing_item and existing_item.get('timestamp') and existing_item['timestamp'].lower() not in ['none', 'null', '']:
                logger.info(f"\tSkip timestamp extraction, existing timestamp found: {existing_item['timestamp']}")
                timestamp_str = existing_item['timestamp']
            else:
                try:
                    timestamp_str = extract_timestamp(photo_file)
                    if timestamp_str:
                        logger.info(f"- Extracted timestamp: {timestamp_str}")
                    else:
                        timestamp_str = ""
                except Exception as e:
                    logger.info(f"Error extracting timestamp for {photo_file.name}: {e}")
                    timestamp_str = ""
        else:
            timestamp_str = existing_item.get('timestamp', '')
        
        ######################
        ## Object detection ##
        ######################
        if run_object_detection:
            if 'objects' in existing_item and existing_item.get('objects'):
                logger.info(f"\tSkip object detection")
                objects_str = existing_item['objects']
            else:
                objects = detect_object(photo_file, 'l', 640)
                objects_str = ",".join(objects) if objects else "None"
                logger.info(f"- Detected objects: {objects_str}")
        else:
            objects_str = existing_item.get('objects', '')

        logger.info(f"{photo_file.name}\n - City: {city}, Country: {country}")
        item = {
            'title': photo_file.stem.replace('-', ' ').replace('_', ' '),
            'image': {
                'src': f"/assets/img/photos_optimized/{optimized_path.name}",
                'alt': photo_file.stem.replace('-', ' ').replace('_', ' ')
            },
            'city': city,
            'country': country,
            'sentiment': sentiments_str,
            'objects': objects_str,
            'color': color_str,
            'timestamp': timestamp_str,
        }
        
        # Update MD file with just this new item
        update_photos_md(item)
        items.append(item)

    logger.info(f"\nFinished! photos.md has been updated with {len(items)} items.")


if __name__ == "__main__":
    max_size_kb = sys.argv[1] if len(sys.argv) > 1 else 500
    max_dimension = 1200
    logger.info(f"Max size for optimized images: {max_size_kb}KB")
    generate_photos_md(max_size_kb, max_dimension, run_sentiment_analysis=False, run_color_analysis=False, run_object_detection=False, run_timestamp=False)
    logger.info(f"Optimization done! Max size for optimized images: {max_size_kb}KB")