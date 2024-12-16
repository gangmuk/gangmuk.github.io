import os
import yaml
from pathlib import Path

def generate_misc_md():
    # Read existing misc.md to preserve front matter structure
    with open('misc.md', 'r', encoding='utf-8') as f:
        existing_content = f.read()
    
    # Extract the existing front matter to preserve special items like video URLs
    existing_items = {}
    if '---' in existing_content:
        parts = existing_content.split('---', 2)
        if len(parts) >= 2:
            try:
                front_matter = yaml.safe_load(parts[1])
                if front_matter and 'items' in front_matter:
                    # Create a dictionary of existing items by title
                    existing_items = {item['title']: item for item in front_matter['items']}
            except yaml.YAMLError:
                pass

    # Generate new items list
    photos_dir = Path("assets/img/photos")
    items = []
    
    # Valid image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.PNG'}
    
    # Scan the directory for image files
    for photo_file in photos_dir.iterdir():
        if photo_file.suffix.lower() in image_extensions:
            title = photo_file.stem.capitalize()
            
            # If this item existed before, preserve its data
            if title in existing_items:
                items.append(existing_items[title])
            else:
                # Create new item
                item = {
                    'title': title,
                    'image': {
                        'src': f"/assets/img/photos/{photo_file.name}",
                        'alt': title
                    },
                    'description': f"Photo taken at {title}"  # Default description
                }
                items.append(item)

    # Create new front matter
    front_matter = {
        'layout': 'misc',
        'title': 'Life',
        'slug': '/misc',
        'items': items
    }

    # Generate the new misc.md content
    '''
    ---
    layout: misc
    title: Life
    slug: /misc
    '''
    content = "---\n"
    content += "layout: misc\n"
    content += "title: Life\n"
    content += "slug: /misc\n"
    content += yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)
    content += "---\n"

    # Write the updated misc.md
    with open('misc.md', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    generate_misc_md()