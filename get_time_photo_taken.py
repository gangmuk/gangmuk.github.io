from PIL import Image
from PIL.ExifTags import TAGS
import os
from datetime import datetime
import argparse
import sys

def extract_timestamp(image_path, debug=False):
    """
    Extract timestamp information from image EXIF data.
    
    Args:
        image_path (str): Path to the image file
        debug (bool): If True, print all EXIF data for debugging
    
    Returns:
        dict: Timestamp analysis results containing:
            - datetime_original: When the photo was taken (primary)
            - datetime_digitized: When the photo was digitized
            - datetime_modified: When the file was last modified
            - camera_info: Camera make and model if available
            - has_exif: Whether EXIF data was found
            - all_exif_data: All EXIF data (if debug=True)
    """
    
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Open image and extract EXIF data
        with Image.open(image_path) as image:
            exif_data = image.getexif()
            
            # Initialize result dictionary
            result = {
                'datetime_original': None,
                'datetime_digitized': None,
                'datetime_modified': None,
                'camera_info': {},
                'has_exif': bool(exif_data),
                'all_timestamps': {},
                'raw_timestamps': {}
            }
            
            if debug:
                result['all_exif_data'] = {}
            
            if not exif_data:
                return result
            
            # Extract relevant EXIF fields
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
                
                if debug:
                    result['all_exif_data'][tag_name] = str(value)
                
                # Look for any field that might contain timestamp data
                if any(keyword in tag_name.lower() for keyword in ['date', 'time']):
                    result['raw_timestamps'][tag_name] = str(value)
                    parsed_dt = parse_exif_datetime(str(value))
                    if parsed_dt:
                        result['all_timestamps'][tag_name] = parsed_dt
                
                # Extract standard timestamp fields
                if tag_name == 'DateTime':
                    result['datetime_modified'] = parse_exif_datetime(str(value))
                elif tag_name == 'DateTimeOriginal':
                    result['datetime_original'] = parse_exif_datetime(str(value))
                elif tag_name == 'DateTimeDigitized':
                    result['datetime_digitized'] = parse_exif_datetime(str(value))
                
                # Extract camera information
                elif tag_name == 'Make':
                    result['camera_info']['make'] = str(value).strip()
                elif tag_name == 'Model':
                    result['camera_info']['model'] = str(value).strip()
                elif tag_name == 'Software':
                    result['camera_info']['software'] = str(value).strip()
            
            # Also check for GPS timestamp
            try:
                gps_info = image.getexif().get_ifd(0x8825)  # GPS IFD
                if gps_info:
                    for tag_id, value in gps_info.items():
                        tag_name = TAGS.get(tag_id, f"GPS_Tag_{tag_id}")
                        if 'date' in tag_name.lower() or 'time' in tag_name.lower():
                            result['raw_timestamps'][f"GPS_{tag_name}"] = str(value)
                            if debug:
                                result['all_exif_data'][f"GPS_{tag_name}"] = str(value)
            except:
                pass
            
            # Determine the primary timestamp (when photo was actually taken)
            primary_timestamp = (result['datetime_original'] or 
                               result['datetime_digitized'])
                               # Removed datetime_modified from primary selection
            
            # If no standard timestamps found, try to use any timestamp we found
            if not primary_timestamp and result['all_timestamps']:
                # Prefer timestamps with 'original' or 'create' in the name
                for name, timestamp in result['all_timestamps'].items():
                    if any(keyword in name.lower() for keyword in ['original', 'create', 'capture']):
                        primary_timestamp = timestamp
                        break
                
                # If still no primary timestamp, use the first one found
                if not primary_timestamp:
                    primary_timestamp = next(iter(result['all_timestamps'].values()))
            
            result['primary_timestamp'] = primary_timestamp
            
            # Add formatted timestamp strings
            if primary_timestamp:
                result['formatted_timestamp'] = primary_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                result['date_only'] = primary_timestamp.strftime('%Y-%m-%d')
                result['time_only'] = primary_timestamp.strftime('%H:%M:%S')
                result['human_readable'] = primary_timestamp.strftime('%B %d, %Y at %I:%M %p')
                return result['formatted_timestamp']  # Return just the formatted timestamp
            
            return None  # Return None if no timestamp found
            
    except Exception as e:
        return None


def parse_exif_datetime(datetime_str):
    """
    Parse EXIF datetime string to datetime object.
    Tries multiple common datetime formats.
    
    Args:
        datetime_str (str): EXIF datetime string
    
    Returns:
        datetime: Parsed datetime object or None if parsing fails
    """
    if not datetime_str or str(datetime_str).strip() == '':
        return None
    
    datetime_str = str(datetime_str).strip()
    
    # List of common datetime formats found in EXIF data
    formats = [
        '%Y:%m:%d %H:%M:%S',      # Standard EXIF format
        '%Y-%m-%d %H:%M:%S',      # ISO format with spaces
        '%Y/%m/%d %H:%M:%S',      # Forward slash format
        '%Y:%m:%d %H:%M',         # Without seconds
        '%Y-%m-%d %H:%M',         # ISO format without seconds
        '%Y/%m/%d %H:%M',         # Forward slash without seconds
        '%Y:%m:%d',               # Date only
        '%Y-%m-%d',               # ISO date only
        '%Y/%m/%d',               # Forward slash date only
        '%m/%d/%Y %H:%M:%S',      # US format with time
        '%m/%d/%Y %H:%M',         # US format without seconds
        '%m/%d/%Y',               # US date only
        '%d/%m/%Y %H:%M:%S',      # European format with time
        '%d/%m/%Y %H:%M',         # European format without seconds
        '%d/%m/%Y',               # European date only
        '%Y%m%d_%H%M%S',          # Compact format with underscore
        '%Y%m%d%H%M%S',           # Compact format no separator
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    
    # If none of the standard formats work, return None
    return None


def get_file_modification_time(image_path):
    """
    Get file system modification time as fallback.
    
    Args:
        image_path (str): Path to the image file
    
    Returns:
        datetime: File modification time
    """
    try:
        timestamp = os.path.getmtime(image_path)
        return datetime.fromtimestamp(timestamp)
    except:
        return None


def print_timestamp_results(result, image_path):
    """
    Print formatted timestamp extraction results.
    
    Args:
        result (dict): Results from extract_timestamp function
        image_path (str): Path to the analyzed image
    """
    print(f"\nTimestamp Analysis for: {os.path.basename(image_path)}")
    print("=" * 50)
    
    if 'error' in result:
        print(f"Error: {result['error']}")
        
        # Try to get file modification time as fallback
        file_mod_time = get_file_modification_time(image_path)
        if file_mod_time:
            print(f"File modification time (fallback): {file_mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    if result['has_exif']:
        print("✓ EXIF data found")
        
        # Primary timestamp
        if result['primary_timestamp']:
            print(f"\nPhoto taken: {result['human_readable']}")
            print(f"Formatted: {result['formatted_timestamp']}")
        else:
            print("\n✗ No valid timestamp found in standard fields")
        
        # Show all timestamps found
        if result['all_timestamps']:
            print(f"\nAll timestamps found:")
            for name, timestamp in result['all_timestamps'].items():
                print(f"  {name}: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show raw timestamps for debugging
        if result['raw_timestamps']:
            print(f"\nRaw timestamp data:")
            for name, raw_value in result['raw_timestamps'].items():
                print(f"  {name}: {raw_value}")
        
        # Standard timestamp breakdown
        if any([result['datetime_original'], result['datetime_digitized'], result['datetime_modified']]):
            print(f"\nStandard EXIF timestamps:")
            if result['datetime_original']:
                print(f"  Original: {result['datetime_original'].strftime('%Y-%m-%d %H:%M:%S')}")
            if result['datetime_digitized']:
                print(f"  Digitized: {result['datetime_digitized'].strftime('%Y-%m-%d %H:%M:%S')}")
            if result['datetime_modified']:
                print(f"  Modified: {result['datetime_modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Camera information
        if result['camera_info'] and any(result['camera_info'].values()):
            print(f"\nCamera information:")
            if result['camera_info'].get('make'):
                print(f"  Make: {result['camera_info']['make']}")
            if result['camera_info'].get('model'):
                print(f"  Model: {result['camera_info']['model']}")
            if result['camera_info'].get('software'):
                print(f"  Software: {result['camera_info']['software']}")
        
        # Debug info
        if 'all_exif_data' in result:
            print(f"\nAll EXIF data:")
            for tag, value in result['all_exif_data'].items():
                print(f"  {tag}: {value}")
    else:
        print("✗ No EXIF data found")
        
        # Try to get file modification time as fallback
        file_mod_time = get_file_modification_time(image_path)
        if file_mod_time:
            print(f"File modification time (fallback): {file_mod_time.strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main function to handle command line arguments and execute timestamp extraction."""
    parser = argparse.ArgumentParser(description='Extract timestamp information from image EXIF data')
    parser.add_argument('image_path', help='Path to the image file')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    parser.add_argument('--debug', action='store_true', help='Show all EXIF data for debugging')
    
    args = parser.parse_args()
    
    # Extract timestamp information
    result = extract_timestamp(args.image_path, debug=args.debug)
    
    if args.json:
        import json
        # Convert datetime objects to strings for JSON serialization
        json_result = result.copy()
        for key in ['datetime_original', 'datetime_digitized', 'datetime_modified', 'primary_timestamp']:
            if json_result.get(key):
                json_result[key] = json_result[key].isoformat()
        
        # Convert all_timestamps dict
        if 'all_timestamps' in json_result:
            for key, value in json_result['all_timestamps'].items():
                json_result['all_timestamps'][key] = value.isoformat()
        
        print(json.dumps(json_result, indent=2))
    else:
        print_timestamp_results(result, args.image_path)


# Example usage and testing function
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If command line arguments provided, use them
        main()
    else:
        # Example usage for testing
        print("Usage: python script.py <image_path> [--debug] [--json]")
        print("Example: python script.py photo.jpg")
        print("  --debug: Show all EXIF data for debugging")
        print("  --json: Output in JSON format")