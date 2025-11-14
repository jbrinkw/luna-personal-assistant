#!/usr/bin/env python3
"""
Interactive Screenshot Annotation Tool

Usage:
    python annotate_tool.py <screenshot_path> <output_path>

Then provide coordinates in the format: x,y,number
Example: 969,394,1

Type 'done' when finished.
"""

import sys
from PIL import Image, ImageDraw, ImageFont

def annotate_screenshot(input_path, output_path, annotations):
    """
    Annotate a screenshot with numbered circles.

    Args:
        input_path: Path to original screenshot
        output_path: Path to save annotated screenshot
        annotations: List of (x, y, number) tuples
    """
    img = Image.open(input_path)
    draw = ImageDraw.Draw(img)

    # Load font
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except:
        font_large = ImageFont.load_default()

    circle_radius = 18

    for x, y, num in annotations:
        # Draw outer white circle
        draw.ellipse(
            [x - circle_radius - 2, y - circle_radius - 2,
             x + circle_radius + 2, y + circle_radius + 2],
            fill='white'
        )
        # Draw red circle
        draw.ellipse(
            [x - circle_radius, y - circle_radius,
             x + circle_radius, y + circle_radius],
            fill='#EF4444',
            outline='white',
            width=3
        )
        # Draw number
        text = str(num)
        bbox = draw.textbbox((0, 0), text, font=font_large)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        draw.text(
            (x - text_width/2, y - text_height/2 - 2),
            text,
            fill='white',
            font=font_large
        )

    img.save(output_path)
    print(f"✓ Saved annotated screenshot to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    img = Image.open(input_path)
    print(f"Image dimensions: {img.size[0]}x{img.size[1]}")
    print("\nEnter annotations in format: x,y,number")
    print("Type 'done' when finished\n")

    annotations = []
    while True:
        line = input("Annotation (x,y,num or 'done'): ").strip()
        if line.lower() == 'done':
            break

        try:
            parts = line.split(',')
            x, y, num = int(parts[0]), int(parts[1]), int(parts[2])
            annotations.append((x, y, num))
            print(f"  Added: ({x}, {y}) = {num}")
        except (ValueError, IndexError):
            print("  Invalid format. Use: x,y,number")

    if annotations:
        annotate_screenshot(input_path, output_path, annotations)
        print(f"\nAnnotated {len(annotations)} points")
    else:
        print("No annotations added")
