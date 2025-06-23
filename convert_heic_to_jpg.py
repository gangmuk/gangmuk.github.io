#!/usr/bin/env python3
"""
HEIC to JPG Converter using macOS sips command
Converts all HEIC files in a target directory to JPG format.

Usage:
    python convert_heic_sips.py <target_directory>
    
Example:
    python convert_heic_sips.py assets/img/photos
"""

import sys
import os
import subprocess
from pathlib import Path

def convert_heic_to_jpg_sips(target_dir, quality=85, remove_original=False):
    """
    Convert all HEIC files in target directory to JPG using macOS sips command.
    
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
    
    # Check if sips command is available (macOS only)
    try:
        subprocess.run(['sips', '--version'], capture_output=True, check=True)
        print("macOS sips command found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: sips command not found. This script only works on macOS.")
        return
    
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
        
        try:
            print(f"Converting: {heic_file.name} -> {jpg_file.name}")
            
            # Use sips to convert HEIC to JPG
            cmd = [
                'sips',
                '-s', 'format', 'jpeg',
                '-s', 'formatOptions', str(quality),
                str(heic_file),
                '--out', str(jpg_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✓ Successfully converted to {jpg_file.name}")
                converted_count += 1
                
                # Remove original if requested
                if remove_original:
                    heic_file.unlink()
                    print(f"  ✓ Removed original {heic_file.name}")
            else:
                print(f"  ✗ Failed to convert {heic_file.name}: {result.stderr}")
                failed_count += 1
                
        except Exception as e:
            print(f"  ✗ Failed to convert {heic_file.name}: {e}")
            failed_count += 1
    
    print(f"\nConversion complete:")
    print(f"  Successfully converted: {converted_count}")
    print(f"  Failed: {failed_count}")
    if remove_original and converted_count > 0:
        print(f"  Original HEIC files removed: {converted_count}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_heic_sips.py <target_directory> [--remove-original] [--quality=85]")
        print("\nOptions:")
        print("  --remove-original    Delete original HEIC files after conversion")
        print("  --quality=N          JPEG quality (1-100, default: 85)")
        print("\nExample:")
        print("  python convert_heic_sips.py assets/img/photos")
        print("  python convert_heic_sips.py assets/img/photos --quality=90 --remove-original")
        print("\nNote: This script uses macOS sips command and only works on macOS.")
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
    
    print(f"Target directory: {target_dir}")
    print(f"JPEG quality: {quality}")
    print(f"Remove originals: {remove_original}")
    print()
    
    convert_heic_to_jpg_sips(target_dir, quality, remove_original)

if __name__ == "__main__":
    main()