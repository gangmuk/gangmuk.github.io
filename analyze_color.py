import cv2
import numpy as np
from collections import Counter
from sklearn.cluster import KMeans
import colorsys

def analyze_color_by_sections(image_path, grid_size=(3, 3), colors_per_section=3, min_percentage=2.0):
    """
    Analyze color by dividing image into grid sections and analyzing each separately.
    
    Args:
        image_path (str): Path to the image file
        grid_size (tuple): Grid dimensions (rows, cols) for sectioning
        colors_per_section (int): Max colors to extract per section
        min_percentage (float): Minimum percentage for a color to be included globally
    
    Returns:
        list: Set of dominant color tags from all sections
    """
    
    FAMILIAR_COLORS = {
        'red': (255, 0, 0),
        'orange': (255, 165, 0),
        'yellow': (255, 255, 0),
        'green': (0, 255, 0),
        'blue': (0, 0, 255),
        'sky_blue': (135, 206, 235),
        'purple': (128, 0, 128),
        'pink': (255, 192, 203),
        'brown': (139, 69, 19),
        'black': (0, 0, 0),
        'white': (255, 255, 255),
        # 'snow_white': (255, 250, 250)
        'gray': (128, 128, 128),
        'bright_gray': (192, 192, 192),
        'navy': (0, 0, 128),
        'olive': (128, 128, 0),
        'gold': (255, 215, 0),
        'beige': (245, 245, 220),
        'lime': (0, 255, 0),
        # 'silver': (192, 192, 192),
        # 'teal': (0, 128, 128),
        # 'maroon': (128, 0, 0),
        # 'turquoise': (64, 224, 208),
        # 'forest_green': (34, 139, 34),
    }
    
    try:
        # Load and preprocess image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image from {image_path}")
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize if too large
        height, width = image_rgb.shape[:2]
        if width > 800 or height > 600:
            scale = min(800/width, 600/height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image_rgb = cv2.resize(image_rgb, (new_width, new_height))
            height, width = new_height, new_width
        
        # Calculate section dimensions
        rows, cols = grid_size
        section_height = height // rows
        section_width = width // cols
        
        all_section_colors = []
        color_frequency = Counter()
        
        # Analyze each section
        for row in range(rows):
            for col in range(cols):
                # Extract section
                y_start = row * section_height
                y_end = (row + 1) * section_height if row < rows - 1 else height
                x_start = col * section_width
                x_end = (col + 1) * section_width if col < cols - 1 else width
                
                section = image_rgb[y_start:y_end, x_start:x_end]
                
                # Analyze section colors
                section_colors = analyze_section_colors(section, FAMILIAR_COLORS, colors_per_section)
                
                # Weight by section size (larger sections contribute more)
                section_size = (y_end - y_start) * (x_end - x_start)
                total_size = height * width
                section_weight = section_size / total_size
                
                # Add to global color frequency with weighting
                for color_info in section_colors:
                    weighted_percentage = color_info['percentage'] * section_weight
                    color_frequency[color_info['familiar_color']] += weighted_percentage
        
        # Filter colors by minimum global percentage
        significant_colors = [
            color for color, freq in color_frequency.items() 
            if freq >= min_percentage
        ]
        
        # Sort by frequency and return top colors
        significant_colors.sort(key=lambda x: color_frequency[x], reverse=True)
        
        return significant_colors[:8]  # Return top 8 colors max
        
    except Exception as e:
        return None


def analyze_section_colors(section, familiar_colors, max_colors=3):
    """
    Analyze colors in a single image section.
    
    Args:
        section (np.array): Image section as numpy array
        familiar_colors (dict): Color mapping dictionary
        max_colors (int): Maximum colors to extract from this section
    
    Returns:
        list: List of color information dictionaries
    """
    # Reshape section to pixel list
    pixels = section.reshape(-1, 3)
    
    # Remove completely uniform areas (likely noise or solid backgrounds)
    if len(np.unique(pixels.reshape(-1))) < 10:
        return []
    
    # Less aggressive filtering - only remove pure black artifacts
    mask = np.sum(pixels, axis=1) > 10  # Only remove near-pure black
    if np.sum(mask) > len(pixels) * 0.1:
        pixels = pixels[mask]
    
    if len(pixels) < 50:  # Skip sections with too few pixels
        return []
    
    # Use fewer clusters for small sections
    n_clusters = min(max_colors, len(pixels) // 20, 5)
    if n_clusters < 1:
        return []
    
    # K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(pixels)
    
    colors = kmeans.cluster_centers_.astype(int)
    labels = kmeans.labels_
    
    # Calculate percentages
    color_counts = Counter(labels)
    total_pixels = len(labels)
    
    section_colors = []
    for i, color in enumerate(colors):
        percentage = (color_counts[i] / total_pixels) * 100
        
        # Lower threshold for section-level analysis
        if percentage >= 10.0:  # 10% within the section
            familiar_color = map_to_familiar_color(tuple(color), familiar_colors)
            section_colors.append({
                'rgb': tuple(color),
                'percentage': percentage,
                'familiar_color': familiar_color
            })
    
    return section_colors


def map_to_familiar_color(rgb_color, familiar_colors):
    """
    Improved color mapping using perceptual distance.
    """
    min_distance = float('inf')
    closest_color = 'unknown'
    
    # Convert to HSV for better perceptual matching
    r, g, b = [x/255.0 for x in rgb_color]
    h1, s1, v1 = colorsys.rgb_to_hsv(r, g, b)
    
    for color_name, color_rgb in familiar_colors.items():
        # Calculate both RGB and HSV distances
        rgb_distance = np.sqrt(sum((a - b) ** 2 for a, b in zip(rgb_color, color_rgb)))
        
        # HSV distance (weighted toward hue and saturation)
        r2, g2, b2 = [x/255.0 for x in color_rgb]
        h2, s2, v2 = colorsys.rgb_to_hsv(r2, g2, b2)
        
        # Hue distance (circular)
        hue_diff = min(abs(h1 - h2), 1 - abs(h1 - h2))
        hsv_distance = np.sqrt(
            (hue_diff * 2) ** 2 +  # Weight hue more heavily
            (s1 - s2) ** 2 +
            (v1 - v2) ** 2
        )
        
        # Combine distances
        combined_distance = rgb_distance * 0.3 + hsv_distance * 100 * 0.7
        
        if combined_distance < min_distance:
            min_distance = combined_distance
            closest_color = color_name
    
    return closest_color


# Alternative: Semantic sectioning based on image content
def analyze_color_semantic_sections(image_path):
    """
    Advanced approach: divide image into semantic regions (sky, ground, etc.)
    This would require more complex image segmentation.
    """
    # This could use:
    # - Top 1/3 for sky analysis
    # - Middle 1/3 for main subjects
    # - Bottom 1/3 for ground/foreground
    # - Edge detection to identify distinct regions
    # - Color-based segmentation to group similar areas
    pass


# Example usage
if __name__ == "__main__":
    image_path = "mountain_image.jpg"
    
    # Grid-based analysis
    colors = analyze_color_by_sections(image_path, grid_size=(3, 3))
    print("Detected colors:", colors)
    
    # For comparison, also try semantic sectioning
    # colors_semantic = analyze_color_semantic_sections(image_path)