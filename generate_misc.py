import os
import yaml
from pathlib import Path
from PIL import Image
import io

def optimize_image(image_path, max_size_kb=500):
    """Optimize image by resizing and compressing until it's under max_size_kb"""
    print(f"\nProcessing {image_path.name}:")
    img = Image.open(image_path)
    
    # Convert RGBA to RGB if necessary
    if img.mode in ('RGBA', 'LA'):
        print(f"  Converting {img.mode} to RGB")
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background

    # Calculate initial size
    temp_buffer = io.BytesIO()
    img.save(temp_buffer, format='JPEG', quality=85)
    current_size = len(temp_buffer.getvalue()) / 1024  # Size in KB
    print(f"  Original size: {current_size:.2f}KB")

    # If image is already small enough, just return optimized version
    if current_size <= max_size_kb:
        print(f"  Image is already under {max_size_kb}KB, skipping optimization")
        return img

    # Calculate new dimensions while maintaining aspect ratio
    max_dimension = 1200
    ratio = min(max_dimension/img.size[0], max_dimension/img.size[1])
    new_size = tuple([int(x*ratio) for x in img.size])
    print(f"  Original dimensions: {img.size}")
    print(f"  New dimensions: {new_size}")
    img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Compress with decreasing quality until size is under max_size_kb
    quality = 85
    while quality > 20:
        temp_buffer = io.BytesIO()
        img.save(temp_buffer, format='JPEG', quality=quality)
        current_size = len(temp_buffer.getvalue()) / 1024
        print(f"  Quality {quality}: {current_size:.2f}KB")
        
        if current_size <= max_size_kb:
            break
            
        quality -= 5

    print(f"  Final size: {current_size:.2f}KB")
    return img

def generate_misc_md():
    # Path to your photos directory and optimized photos directory
    photos_dir = Path("assets/img/photos")
    optimized_dir = Path("assets/img/photos_optimized")
    print(f"\nCreating optimized directory: {optimized_dir}")
    optimized_dir.mkdir(exist_ok=True)

    # List to store photo items
    items = []
    
    # Valid image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.PNG'}
    
    # Process each image
    total_files = len([f for f in photos_dir.iterdir() if f.suffix.lower() in image_extensions])
    print(f"\nFound {total_files} images to process")
    
    processed = 0
    for photo_file in photos_dir.iterdir():
        if photo_file.suffix.lower() in image_extensions:
            processed += 1
            print(f"\nProcessing file {processed}/{total_files}: {photo_file.name}")
            # optimized_path = optimized_dir / f"{photo_file.stem}_optimized.jpg"
            optimized_path = optimized_dir / f"{photo_file.stem}_optimized{photo_file.suffix}"
            
            # Optimize image if not already optimized
            if not optimized_path.exists():
                try:
                    optimized_img = optimize_image(photo_file)
                    optimized_img.save(optimized_path, 'JPEG', quality=85)
                    print(f"Saved optimized image to: {optimized_path}")
                except Exception as e:
                    print(f"Error processing {photo_file}: {e}")
                    continue
            else:
                print("Optimized version already exists, skipping")

            # Create item entry with optimized image path
            item = {
                'title': photo_file.stem.replace('-', ' ').replace('_', ' '),
                'image': {
                    'src': f"/assets/img/photos_optimized/{optimized_path.name}",
                    'alt': photo_file.stem.replace('-', ' ').replace('_', ' ')
                }
            }
            items.append(item)

    print(f"\nGenerating misc.md with {len(items)} items")
    # Create front matter
    front_matter = {
        'layout': 'misc',
        'title': 'Life',
        'slug': '/misc',
        'items': items
    }

    # Generate the misc.md content
    content = "---\n"
    content += yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)
    content += "---\n"

    # Write to misc.md
    with open('misc.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print("\nFinished! misc.md has been updated.")

if __name__ == "__main__":
    generate_misc_md()