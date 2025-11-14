#!/root/luna-personal-assistant/.venv/bin/python3
"""
Update Visual Walkthrough Documentation

Updates the existing visual-walkthrough.md file by replacing placeholder
image map coordinates with actual values from annotation JSON files.
"""

import json
import re
from pathlib import Path


def slugify(text):
    """Convert text to URL-friendly slug"""
    return text.lower().replace(' ', '-').replace('/', '-').replace('&', 'and').replace('(', '').replace(')', '')


def load_annotations():
    """Load all annotation JSON files"""
    annotations_dir = Path("docs/tutorial_screenshots/annotated")
    annotations = {}

    for json_file in annotations_dir.glob("*_annotations.json"):
        with open(json_file) as f:
            data = json.load(f)
            image_name = data['image']
            annotations[image_name] = data['markers']

    return annotations


def generate_image_map(image_name, markers, map_name):
    """Generate HTML image map markup"""
    lines = []
    lines.append(f'<div style="position: relative; display: inline-block;">')
    lines.append(f'  <img src="../tutorial_screenshots/annotated/{image_name}" usemap="#{map_name}" style="max-width: 100%; height: auto;" />')
    lines.append(f'  <map name="{map_name}">')

    # Sort markers by number
    sorted_markers = sorted(markers, key=lambda m: int(m['number']))

    for marker in sorted_markers:
        bounds = marker['bounds']
        slug = slugify(marker['label'])
        coords = f"{bounds['x1']},{bounds['y1']},{bounds['x2']},{bounds['y2']}"
        lines.append(f'    <area shape="rect" coords="{coords}" href="#{slug}" alt="{marker["label"]}" />')

    lines.append(f'  </map>')
    lines.append(f'</div>')

    return '\n'.join(lines)


def update_walkthrough(doc_path="docs/user-guide/visual-userguide.md"):
    """Update the visual walkthrough document with real image map coordinates"""

    # Load all annotations
    annotations = load_annotations()

    # Read the current document
    with open(doc_path, 'r') as f:
        content = f.read()

    # Define replacements for each annotated screenshot
    replacements = {
        'hub_home_dashboard.png': {
            'pattern': r'<div style="position: relative; display: inline-block;">\s*<img src="\.\./tutorial_screenshots/annotated/hub_home_dashboard\.png" usemap="#[^"]*"[^>]*>\s*<map name="[^"]*">.*?</map>\s*</div>',
            'map_name': 'hub-home-map',
            'placeholder': '[CLICKABLE IMAGE MAP WITH 12 MARKERS - hub_home_dashboard.png]'
        },
        'addon_store_configure_extension.png': {
            'pattern': r'<div style="position: relative; display: inline-block;">\s*<img src="\.\./tutorial_screenshots/annotated/addon_store_configure_extension\.png" usemap="#[^"]*"[^>]*>\s*<map name="[^"]*">.*?</map>\s*</div>',
            'map_name': 'configure-map',
            'placeholder': None
        },
        'tool_mcp_manager.png': {
            'pattern': r'<div style="position: relative; display: inline-block;">\s*<img src="\.\./tutorial_screenshots/annotated/tool_mcp_manager\.png" usemap="#[^"]*"[^>]*>\s*<map name="[^"]*">.*?</map>\s*</div>',
            'map_name': 'tool-manager-map',
            'placeholder': None
        },
        'quick_chat_interface.png': {
            'pattern': r'<div style="position: relative; display: inline-block;">\s*<img src="\.\./tutorial_screenshots/annotated/quick_chat_interface\.png" usemap="#[^"]*"[^>]*>\s*<map name="[^"]*">.*?</map>\s*</div>',
            'map_name': 'quick-chat-map',
            'placeholder': None
        },
        'walmart_manager.png': {
            'pattern': r'<div style="position: relative; display: inline-block;">\s*<img src="\.\./tutorial_screenshots/annotated/walmart_manager\.png" usemap="#[^"]*"[^>]*>\s*<map name="[^"]*">.*?</map>\s*</div>',
            'map_name': 'walmart-map',
            'placeholder': None
        },
        'scanner_io_wizard_with_items.png': {
            'pattern': r'<div style="position: relative; display: inline-block;">\s*<img src="\.\./tutorial_screenshots/annotated/scanner_io_wizard_with_items\.png" usemap="#[^"]*"[^>]*>\s*<map name="[^"]*">.*?</map>\s*</div>',
            'map_name': 'scanner-map',
            'placeholder': None
        }
    }

    # Replace each image map placeholder with actual coordinates
    for image_name, config in replacements.items():
        if image_name not in annotations:
            print(f"⚠ Warning: No annotations found for {image_name}")
            continue

        # Generate the new image map HTML
        new_map = generate_image_map(image_name, annotations[image_name], config['map_name'])

        # Replace placeholder text if it exists
        if config['placeholder']:
            if config['placeholder'] in content:
                content = content.replace(config['placeholder'], new_map)
                print(f"✓ Updated placeholder for {image_name}")
            else:
                print(f"⚠ Placeholder not found for {image_name}: {config['placeholder']}")

        # Also replace existing image map if it exists
        pattern = config['pattern']
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_map, content, flags=re.DOTALL)
            print(f"✓ Updated existing map for {image_name}")

    # Write the updated content back
    with open(doc_path, 'w') as f:
        f.write(content)

    print(f"\n✓ Updated {doc_path}")
    return doc_path


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Visual Walkthrough Image Map Updater")
    print("="*60 + "\n")

    result = update_walkthrough()

    print("\n" + "="*60)
    print("✓ Done! Image maps updated with real coordinates.")
    print("="*60 + "\n")
