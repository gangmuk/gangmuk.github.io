import cv2
import numpy as np
from collections import Counter
from sklearn.cluster import KMeans
import colorsys

def analyze_color(image_path, num_colors=5, min_percentage=5.0):
    """
    Analyze the color profile of an image and return dominant colors mapped to familiar color names.
    
    Args:
        image_path (str): Path to the image file
        num_colors (int): Number of dominant colors to extract (default: 5)
        min_percentage (float): Minimum percentage threshold for a color to be included (default: 5.0)
    
    Returns:
        dict: Color analysis results containing:
            - dominant_colors: List of dominant colors with percentages
            - color_tags: List of familiar color names for searching
            - primary_color: The most dominant color
    """
    
    # Define familiar color palette for mapping
    FAMILIAR_COLORS = {
        'red': (255, 0, 0),
        'orange': (255, 165, 0),
        'yellow': (255, 255, 0),
        'green': (0, 255, 0),
        'blue': (0, 0, 255),
        'purple': (128, 0, 128),
        'pink': (255, 192, 203),
        'brown': (139, 69, 19),
        'black': (0, 0, 0),
        'white': (255, 255, 255),
        'gray': (128, 128, 128),
        'navy': (0, 0, 128),
        'teal': (0, 128, 128),
        'lime': (0, 255, 0),
        'maroon': (128, 0, 0),
        'olive': (128, 128, 0),
        'silver': (192, 192, 192),
        'gold': (255, 215, 0),
        'beige': (245, 245, 220),
        'turquoise': (64, 224, 208)
    }
    
    try:
        # Load and preprocess image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image from {image_path}")
        
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize image for faster processing if it's too large
        height, width = image_rgb.shape[:2]
        if width > 800 or height > 600:
            scale = min(800/width, 600/height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image_rgb = cv2.resize(image_rgb, (new_width, new_height))
        
        # Reshape image to be a list of pixels
        pixels = image_rgb.reshape(-1, 3)
        
        # Remove pixels that are too close to pure black or white (likely noise)
        # Keep pixels that aren't too dark or too bright
        mask = np.logical_and(
            np.sum(pixels, axis=1) > 30,  # Not too dark
            np.sum(pixels, axis=1) < 735  # Not too bright
        )
        if np.sum(mask) > len(pixels) * 0.1:  # If we have enough non-extreme pixels
            pixels = pixels[mask]
        
        # Use KMeans clustering to find dominant colors
        kmeans = KMeans(n_clusters=min(num_colors, len(pixels)), random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # Get colors and their frequencies
        colors = kmeans.cluster_centers_.astype(int)
        labels = kmeans.labels_
        
        # Calculate percentages
        color_counts = Counter(labels)
        total_pixels = len(labels)
        
        # Create results
        dominant_colors = []
        color_tags = set()
        
        for i, color in enumerate(colors):
            percentage = (color_counts[i] / total_pixels) * 100
            
            # Only include colors above minimum percentage threshold
            if percentage >= min_percentage:
                # Map to familiar color
                familiar_color = map_to_familiar_color(tuple(color), FAMILIAR_COLORS)
                
                dominant_colors.append({
                    'rgb': tuple(color),
                    'hex': rgb_to_hex(tuple(color)),
                    'percentage': round(percentage, 2),
                    'familiar_color': familiar_color
                })
                
                color_tags.add(familiar_color)
        
        # Sort by percentage (descending)
        dominant_colors.sort(key=lambda x: x['percentage'], reverse=True)
        
        # Determine primary color
        primary_color = dominant_colors[0]['familiar_color'] if dominant_colors else 'unknown'
        
        # return {
        #     'dominant_colors': dominant_colors,
        #     'color_tags': list(color_tags),
        #     'primary_color': primary_color,
        #     'total_colors_found': len(dominant_colors)
        # }
        return list(color_tags)
        
    except Exception as e:
        return None
        # return {
        #     'error': str(e),
        #     'dominant_colors': [],
        #     'color_tags': [],
        #     'primary_color': 'unknown',
        #     'total_colors_found': 0
        # }


def map_to_familiar_color(rgb_color, familiar_colors):
    """
    Map an RGB color to the nearest familiar color name.
    
    Args:
        rgb_color (tuple): RGB color tuple (r, g, b)
        familiar_colors (dict): Dictionary of familiar color names and their RGB values
    
    Returns:
        str: Name of the nearest familiar color
    """
    min_distance = float('inf')
    closest_color = 'unknown'
    
    for color_name, color_rgb in familiar_colors.items():
        # Calculate Euclidean distance in RGB space
        distance = np.sqrt(sum((a - b) ** 2 for a, b in zip(rgb_color, color_rgb)))
        
        if distance < min_distance:
            min_distance = distance
            closest_color = color_name
    
    return closest_color


def rgb_to_hex(rgb):
    """Convert RGB tuple to hex string."""
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])


def get_color_brightness(rgb):
    """Calculate the perceived brightness of a color."""
    # Using luminance formula
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def get_color_saturation(rgb):
    """Calculate the saturation of a color."""
    r, g, b = [x/255.0 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return s


# Example usage and testing function
if __name__ == "__main__":
    # Example usage
    image_path = "example_image.jpg"  # Replace with actual image path
    
    result = analyze_color(image_path)
    
    if 'error' not in result:
        print("Color Analysis Results:")
        print(f"Primary Color: {result['primary_color']}")
        print(f"Color Tags: {', '.join(result['color_tags'])}")
        print(f"Total Colors Found: {result['total_colors_found']}")
        print("\nDominant Colors:")
        
        for color_info in result['dominant_colors']:
            print(f"  - {color_info['familiar_color']}: {color_info['percentage']}% "
                  f"(RGB: {color_info['rgb']}, Hex: {color_info['hex']})")
    else:
        print(f"Error: {result['error']}")