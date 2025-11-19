#!/root/luna-personal-assistant/.venv/bin/python3
"""
Documentation Generator for Annotated Screenshots

Reads annotation JSON files and generates Markdown documentation
with clickable image maps that link to section anchors.
"""

import json
import os
from pathlib import Path


def slugify(text):
    """Convert text to URL-friendly slug"""
    return text.lower().replace(' ', '-').replace('/', '-').replace('&', 'and')


def generate_markdown(annotation_json_path, output_md_path=None):
    """
    Generate Markdown documentation from annotation JSON.

    Args:
        annotation_json_path: Path to the _annotations.json file
        output_md_path: Optional output path for the .md file
    """
    # Load annotation data
    with open(annotation_json_path) as f:
        data = json.load(f)

    image_name = data['image']
    markers = data['markers']

    # Default output path if not provided
    if output_md_path is None:
        base_name = image_name.rsplit('.', 1)[0]
        output_md_path = f"docs/user-guide/{base_name.replace('_', '-')}.md"

    # Sort markers by number
    markers.sort(key=lambda m: int(m['number']))

    # Generate page title from filename
    page_title = image_name.rsplit('.', 1)[0].replace('_', ' ').title()

    # Load image dimensions to include explicit width/height so image maps stay clickable when scaled
    from PIL import Image
    img_path = Path("docs/tutorial_screenshots/annotated") / image_name
    if img_path.exists():
        width, height = Image.open(img_path).size
    else:
        width = height = None

    # Build Markdown content
    lines = []
    lines.append(f"# {page_title}\n")
    lines.append(f'<div style="position: relative; display: inline-block;">')
    size_attrs = f' width="{width}" height="{height}"' if width and height else ""
    lines.append(f'  <img src="/tutorial_screenshots/annotated/{image_name}" usemap="#screenshot-map" style="max-width: 100%; height: auto;"{size_attrs} />')
    lines.append(f'  <map name="screenshot-map">')

    # Add clickable areas
    for marker in markers:
        bounds = marker['bounds']
        slug = slugify(marker['label'])
        coords = f"{bounds['x1']},{bounds['y1']},{bounds['x2']},{bounds['y2']}"
        lines.append(f'    <area shape="rect" coords="{coords}" href="#{slug}" alt="{marker["label"]}" />')

    lines.append(f'  </map>')
    lines.append(f'</div>\n')

    # Add navigation/reference section
    lines.append(f"## Quick Reference\n")
    for marker in markers:
        slug = slugify(marker['label'])
        lines.append(f"{marker['number']}. [{marker['label']}](#{slug})")
    lines.append("")

    lines.append("---\n")

    # Add section stubs for each marker
    for marker in markers:
        slug = slugify(marker['label'])
        lines.append(f"## {marker['label']} {{: #{slug} }}\n")
        lines.append(f"<!-- TODO: Add detailed explanation for {marker['label']} -->\n")
        lines.append(f"Description of the **{marker['label']}** feature goes here.\n")
        lines.append("")

    # Write output file
    os.makedirs(os.path.dirname(output_md_path), exist_ok=True)
    with open(output_md_path, 'w') as f:
        f.write('\n'.join(lines))

    return output_md_path


def generate_all_docs(annotations_dir="docs/tutorial_screenshots/annotated"):
    """Generate documentation for all annotation JSON files"""
    annotations_dir = Path(annotations_dir)
    generated_files = []

    for json_file in annotations_dir.glob("*_annotations.json"):
        try:
            output_path = generate_markdown(str(json_file))
            generated_files.append(output_path)
            print(f"✓ Generated: {output_path}")
        except Exception as e:
            print(f"✗ Error processing {json_file}: {e}")

    return generated_files


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Generate for specific JSON file
        json_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        result = generate_markdown(json_path, output_path)
        print(f"\n✓ Generated documentation: {result}")
    else:
        # Generate for all annotations
        print("\n" + "="*60)
        print("Documentation Generator")
        print("="*60 + "\n")
        files = generate_all_docs()
        print(f"\n✓ Generated {len(files)} documentation files")
        print("="*60 + "\n")
