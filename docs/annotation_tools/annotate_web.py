#!/root/luna-personal-assistant/.venv/bin/python3
"""
Web-based screenshot annotation tool.
Drag numbered markers onto the image, click Done to save.
"""

from flask import Flask, render_template_string, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import json
import base64
import io
import os

app = Flask(__name__)

# Global state
current_image_path = None
current_markers = {}
original_image = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Screenshot Annotator</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: white;
        }
        h1 { margin: 0 0 20px 0; }
        #container {
            position: relative;
            display: inline-block;
            background: #2a2a2a;
            padding: 10px;
            border-radius: 8px;
        }
        #canvas {
            border: 2px solid #444;
            cursor: crosshair;
            display: block;
        }
        .marker {
            position: absolute;
            min-width: 40px;
            height: 40px;
            background: #EF4444;
            border: 3px solid white;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 14px;
            cursor: move;
            user-select: none;
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            touch-action: none;
            z-index: 1000;
            padding: 0 12px;
            white-space: nowrap;
            /* Better touch target size */
            min-height: 44px;
            /* Prevent text selection on touch */
            -webkit-touch-callout: none;
        }
        .marker:hover {
            transform: scale(1.1);
        }
        .marker:active {
            transform: scale(1.05);
        }
        .marker.dragging {
            opacity: 0.8;
            z-index: 2000;
            transform: scale(1.1);
        }
        #buttons {
            margin-top: 20px;
        }
        button {
            padding: 12px 30px;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin-right: 10px;
        }
        #done-btn {
            background: #22c55e;
            color: white;
        }
        #done-btn:hover {
            background: #16a34a;
        }
        #cancel-btn {
            background: #ef4444;
            color: white;
        }
        #cancel-btn:hover {
            background: #dc2626;
        }
        #status {
            margin-top: 10px;
            padding: 10px;
            border-radius: 5px;
            display: none;
        }
        #status.success {
            background: #22c55e;
            display: block;
        }
        #status.error {
            background: #ef4444;
            display: block;
        }
    </style>
</head>
<body>
    <h1>Screenshot Annotator</h1>
    <p>Drag the labeled markers to point at their UI elements on the screenshot, then click Done.</p>
    <p style="font-size: 14px; color: #aaa;">Tip: Position markers next to (not covering) their target elements for best visibility.</p>

    <div id="container">
        <img id="canvas" src="/image" />
        <!-- Markers will be inserted here -->
    </div>

    <div id="buttons">
        <button id="done-btn" onclick="save()">Done - Save Annotation</button>
        <button id="cancel-btn" onclick="window.close()">Cancel</button>
    </div>

    <div id="status"></div>

    <script>
        const markers = {{ markers_json | safe }};
        const container = document.getElementById('container');
        const canvas = document.getElementById('canvas');

        let draggedMarker = null;
        let offsetX = 0;
        let offsetY = 0;

        // Wait for image to load
        canvas.onload = function() {
            // Create markers
            Object.keys(markers).forEach(num => {
                const marker = document.createElement('div');
                marker.className = 'marker';
                marker.textContent = num + ' - ' + markers[num];
                marker.dataset.num = num;
                marker.style.left = (50 + (parseInt(num) - 1) * 10) + 'px';
                marker.style.top = (50 + (parseInt(num) - 1) * 50) + 'px';

                // Add both mouse and touch event listeners
                marker.addEventListener('mousedown', startDrag);
                marker.addEventListener('touchstart', startDrag, {passive: false});
                container.appendChild(marker);
            });
        };

        function getClientPosition(e) {
            // Unified function to get client position from mouse or touch event
            if (e.touches && e.touches.length > 0) {
                return {
                    clientX: e.touches[0].clientX,
                    clientY: e.touches[0].clientY
                };
            }
            return {
                clientX: e.clientX,
                clientY: e.clientY
            };
        }

        function startDrag(e) {
            e.preventDefault(); // Prevent default touch behavior (scrolling, etc.)

            draggedMarker = e.target;
            draggedMarker.classList.add('dragging');

            const rect = draggedMarker.getBoundingClientRect();
            const pos = getClientPosition(e);

            offsetX = pos.clientX - rect.left;
            offsetY = pos.clientY - rect.top;

            // Add both mouse and touch move/end listeners
            document.addEventListener('mousemove', drag);
            document.addEventListener('mouseup', stopDrag);
            document.addEventListener('touchmove', drag, {passive: false});
            document.addEventListener('touchend', stopDrag);
            document.addEventListener('touchcancel', stopDrag);
        }

        function drag(e) {
            if (!draggedMarker) return;
            e.preventDefault(); // Prevent scrolling while dragging

            const containerRect = container.getBoundingClientRect();
            const pos = getClientPosition(e);

            let x = pos.clientX - containerRect.left - offsetX;
            let y = pos.clientY - containerRect.top - offsetY;

            // Keep marker within bounds
            x = Math.max(0, Math.min(x, containerRect.width - 40));
            y = Math.max(0, Math.min(y, containerRect.height - 40));

            draggedMarker.style.left = x + 'px';
            draggedMarker.style.top = y + 'px';
        }

        function stopDrag() {
            if (draggedMarker) {
                draggedMarker.classList.remove('dragging');
                draggedMarker = null;
            }
            // Remove all event listeners
            document.removeEventListener('mousemove', drag);
            document.removeEventListener('mouseup', stopDrag);
            document.removeEventListener('touchmove', drag);
            document.removeEventListener('touchend', stopDrag);
            document.removeEventListener('touchcancel', stopDrag);
        }

        function save() {
            const positions = {};
            const canvasRect = canvas.getBoundingClientRect();
            const naturalWidth = canvas.naturalWidth || canvas.width;
            const naturalHeight = canvas.naturalHeight || canvas.height;
            const scaleX = naturalWidth / canvasRect.width;
            const scaleY = naturalHeight / canvasRect.height;

            document.querySelectorAll('.marker').forEach(marker => {
                const num = marker.dataset.num;
                const rect = marker.getBoundingClientRect();

                const width = rect.width;
                const height = rect.height;
                const centerX = rect.left - canvasRect.left + (width / 2);
                const centerY = rect.top - canvasRect.top + (height / 2);

                positions[num] = {
                    x: Math.round(centerX * scaleX),
                    y: Math.round(centerY * scaleY),
                    width: Math.round(width * scaleX),
                    height: Math.round(height * scaleY)
                };
            });

            fetch('/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(positions)
            })
            .then(r => r.json())
            .then(data => {
                const status = document.getElementById('status');
                if (data.success) {
                    status.className = 'success';
                    status.textContent = '✓ Saved! Go back to terminal and press CTRL+C to continue to next screenshot.';
                } else {
                    status.className = 'error';
                    status.textContent = 'Error: ' + data.error;
                }
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, markers_json=json.dumps(current_markers))

@app.route('/image')
def get_image():
    return send_file(current_image_path)

@app.route('/save', methods=['POST'])
def save():
    try:
        positions = request.json

        # Load original image
        img = Image.open(current_image_path)
        draw = ImageDraw.Draw(img)

        # Prepare font for labels
        try:
            label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except:
            label_font = ImageFont.load_default()

        # Prepare annotation data for JSON export
        annotation_data = {
            "image": os.path.basename(current_image_path),
            "markers": []
        }

        img_width, img_height = img.size

        # Draw markers with labels
        for num, pos in positions.items():
            x, y = pos['x'], pos['y']

            # Get the label text
            label = current_markers.get(num, f"Item {num}")
            full_text = f"{num} - {label}"

            # Calculate text dimensions
            text_bbox = label_font.getbbox(full_text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            padding_x = 12
            padding_y = 10
            requested_width = pos.get('width')
            requested_height = pos.get('height')

            rect_width = requested_width if requested_width else text_width + (padding_x * 2)
            rect_height = requested_height if requested_height else text_height + (padding_y * 2)

            rect_width = max(rect_width, text_width + (padding_x * 2))
            rect_height = max(rect_height, text_height + (padding_y * 2))

            half_w = rect_width / 2
            half_h = rect_height / 2

            # Clamp within image bounds
            x1 = max(0, x - half_w)
            y1 = max(0, y - half_h)
            x2 = min(img_width, x + half_w)
            y2 = min(img_height, y + half_h)

            effective_width = x2 - x1
            effective_height = y2 - y1
            radius = min(effective_height / 2, effective_width / 2)

            # White outline background
            outline_pad = 2
            draw.rounded_rectangle(
                [x1 - outline_pad, y1 - outline_pad, x2 + outline_pad, y2 + outline_pad],
                radius=radius + outline_pad,
                fill='white'
            )

            # Red background
            draw.rounded_rectangle(
                [x1, y1, x2, y2],
                radius=radius,
                fill='#EF4444',
                outline='white',
                width=3
            )

            # Draw text centered
            text_x = x - text_width / 2
            text_y = y - text_height / 2 - text_bbox[1]
            draw.text((text_x, text_y), full_text, fill='white', font=label_font)

            # Store annotation data for JSON
            annotation_data["markers"].append({
                "number": num,
                "label": label,
                "position": {"x": int(x), "y": int(y)},
                "bounds": {
                    "x1": int(x1),
                    "y1": int(y1),
                    "x2": int(x2),
                    "y2": int(y2)
                },
                "size": {
                    "width": int(effective_width),
                    "height": int(effective_height)
                }
            })

        # Save annotated image
        output_dir = "docs/tutorial_screenshots/annotated"
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.basename(current_image_path)
        output_path = os.path.join(output_dir, filename)
        img.save(output_path)

        # Save position data as JSON
        json_filename = filename.rsplit('.', 1)[0] + '_annotations.json'
        json_path = os.path.join(output_dir, json_filename)
        with open(json_path, 'w') as f:
            json.dump(annotation_data, f, indent=2)

        return jsonify({"success": True, "path": output_path, "json_path": json_path})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python annotate_web.py <image_path> [markers.json]")
        sys.exit(1)

    current_image_path = sys.argv[1]

    if len(sys.argv) >= 3:
        with open(sys.argv[2]) as f:
            current_markers = json.load(f)
    else:
        current_markers = {"1": "Marker 1", "2": "Marker 2", "3": "Marker 3"}

    print("\n" + "="*60)
    print("Screenshot Annotation Tool")
    print("="*60)
    print(f"\nImage: {current_image_path}")
    print(f"Markers: {len(current_markers)}")
    print("\nOpen this URL in your browser:")
    print("  http://localhost:5555")
    print("\nDrag the markers to their positions, then click Done.")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5555, debug=False)
