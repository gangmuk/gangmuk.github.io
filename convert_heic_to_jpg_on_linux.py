#!/usr/bin/env python3
"""
Cross-platform HEIC to JPG Converter
Converts all HEIC files in a target directory to JPG format.
Works on macOS (using sips) and Linux (using pillow-heif).

Usage:
    python convert_heic_cross_platform.py <target_directory>
    
Example:
    python convert_heic_cross_platform.py assets/img/photos
"""

import sys
import os
import subprocess
import platform
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are available"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        try:
            subprocess.run(['sips', '--version'], capture_output=True, check=True)
            return "sips"
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: sips command not found on macOS. Falling back to pillow-heif")
            return "pillow-heif"
    
    elif system == "Linux":
        return "pillow-heif"
    
    else:
        print(f"Warning: Unsupported operating system: {system}")
        return "pillow-heif"

def convert_with_sips(heic_file, jpg_file, quality):
    """Convert using macOS sips command"""
    cmd = [
        'sips',
        '-s', 'format', 'jpeg',
        '-s', 'formatOptions', str(quality),
        str(heic_file),
        '--out', str(jpg_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr

def convert_with_pillow_heif(heic_file, jpg_file, quality):
    """Convert using pillow-heif (works on Linux and macOS)"""
    try:
        from PIL import Image
        import pillow_heif
        
        # Register HEIF opener with Pillow
        pillow_heif.register_heif_opener()
        
        # Open HEIC file and convert to JPG
        with Image.open(heic_file) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as JPG
            img.save(jpg_file, 'JPEG', quality=quality, optimize=True)
        
        return True, None
        
    except ImportError as e:
        return False, f"Missing dependency: {e}. Install with: pip install pillow-heif"
    except Exception as e:
        return False, str(e)

def convert_heic_to_jpg(target_dir, quality=85, remove_original=False):
    """
    Convert all HEIC files in target directory to JPG.
    
    Args:
        target_dir (str): Directory containing HEIC files
        quality (int): JPEG quality (1-100, default 85)
        remove_original (bool): Whether to delete original HEIC files
    """
    target_path = Path(target_dir)
    
    if not target_path.exists():
        print(f"Error: Directory '{target_dir}' does not exist")
        return
    
    if not target_path.is_dir():
        print(f"Error: '{target_dir}' is not a directory")
        return
    
    # Check which conversion method to use
    method = check_dependencies()
    print(f"Using conversion method: {method}")
    
    # Find all HEIC files
    heic_files = []
    for ext in ['*.heic', '*.HEIC']:
        heic_files.extend(target_path.glob(ext))
    
    if not heic_files:
        print(f"No HEIC files found in '{target_dir}'")
        return
    
    print(f"Found {len(heic_files)} HEIC files to convert")
    
    converted_count = 0
    failed_count = 0
    
    for heic_file in heic_files:
        jpg_file = heic_file.with_suffix('.jpg')
        
        # Skip if JPG already exists
        if jpg_file.exists():
            print(f"Skipping {heic_file.name} - {jpg_file.name} already exists")
            continue
        
        print(f"Converting: {heic_file.name} -> {jpg_file.name}")
        
        # Convert based on available method
        if method == "sips":
            success, error_msg = convert_with_sips(heic_file, jpg_file, quality)
        else:
            success, error_msg = convert_with_pillow_heif(heic_file, jpg_file, quality)
        
        if success:
            print(f"  ✓ Successfully converted to {jpg_file.name}")
            converted_count += 1
            
            # Remove original if requested
            if remove_original:
                heic_file.unlink()
                print(f"  ✓ Removed original {heic_file.name}")
        else:
            print(f"  ✗ Failed to convert {heic_file.name}: {error_msg}")
            failed_count += 1
    
    print(f"\nConversion complete:")
    print(f"  Successfully converted: {converted_count}")
    print(f"  Failed: {failed_count}")
    if remove_original and converted_count > 0:
        print(f"  Original HEIC files removed: {converted_count}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_heic_cross_platform.py <target_directory> [--remove-original] [--quality=85]")
        print("\nOptions:")
        print("  --remove-original    Delete original HEIC files after conversion")
        print("  --quality=N          JPEG quality (1-100, default: 85)")
        print("\nExample:")
        print("  python convert_heic_cross_platform.py assets/img/photos")
        print("  python convert_heic_cross_platform.py assets/img/photos --quality=90 --remove-original")
        print("\nNote: On Linux, requires 'pillow-heif' package: pip install pillow-heif")
        sys.exit(1)
    
    target_dir = sys.argv[1]
    remove_original = '--remove-original' in sys.argv
    
    # Parse quality setting
    quality = 85
    for arg in sys.argv:
        if arg.startswith('--quality='):
            try:
                quality = int(arg.split('=')[1])
                if not 1 <= quality <= 100:
                    print("Error: Quality must be between 1 and 100")
                    sys.exit(1)
            except ValueError:
                print("Error: Invalid quality value")
                sys.exit(1)
    
    print(f"Operating System: {platform.system()}")
    print(f"Target directory: {target_dir}")
    print(f"JPEG quality: {quality}")
    print(f"Remove originals: {remove_original}")
    print()
    
    convert_heic_to_jpg(target_dir, quality, remove_original)

if __name__ == "__main__":
    main()