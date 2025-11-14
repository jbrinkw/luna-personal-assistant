# Screenshot Annotation Tools

This directory contains tools for creating and maintaining the annotated screenshots used in Luna's Visual User Guide documentation.

## Directory Structure

```
annotation_tools/
├── markers/                      # JSON files defining marker labels for each screenshot
│   ├── hub_home_markers.json
│   ├── addon_store_markers.json
│   └── ... (14 total marker definition files)
├── annotate_web.py               # Flask web app for interactive annotation
├── annotate_all.sh               # Sequential workflow to annotate all screenshots
├── update_visual_walkthrough.py  # Updates docs with real image map coordinates
└── generate_docs.py              # Original documentation generator
```

## Usage

### Annotating Screenshots

Run from the repository root:

```bash
cd /root/luna-personal-assistant
./docs/annotation_tools/annotate_all.sh
```

This will:
1. Guide you through each screenshot that needs markers
2. Start a web server at http://192.168.0.166:5555
3. Let you drag markers onto the image
4. Save annotations to `docs/tutorial_screenshots/annotated/`
5. Continue to the next screenshot

### Updating Documentation

After annotating screenshots, update the Visual User Guide:

```bash
cd /root/luna-personal-assistant
.venv/bin/python3 docs/annotation_tools/update_visual_walkthrough.py
```

This reads the annotation JSON files and updates the clickable image maps in `docs/user-guide/visual-userguide.md`.

## Marker Definitions

Each `*_markers.json` file maps numbers to labels:

```json
{
  "1": "Browse Store",
  "2": "Tool Manager",
  "3": "Manage Secrets"
}
```

- **Non-empty markers**: Screenshot will be annotated with clickable regions
- **Empty markers (`{}`)**: Screenshot used as visual reference only (no clickable markers)

## Files Reference

- **annotate_web.py**: Flask app with touch + mouse support for dragging markers
- **annotate_all.sh**: Sequential workflow script that processes all screenshots
- **update_visual_walkthrough.py**: Generates HTML image maps from annotation JSON
- **generate_docs.py**: Original documentation generator (legacy)
- **markers/*.json**: Marker label definitions (14 files total)

## Output

Annotated screenshots are saved to:
- **Images**: `docs/tutorial_screenshots/annotated/*_annotated.png`
- **Coordinates**: `docs/tutorial_screenshots/annotated/*_annotations.json`

These files are used by `update_visual_walkthrough.py` to create the clickable documentation.
