#!/bin/bash
# Annotate All Screenshots - Sequential Workflow
# Goes through all screenshots one by one without restarting

echo "========================================="
echo "Luna Screenshot Annotation - All Screenshots"
echo "========================================="
echo ""
echo "This will guide you through annotating all 14 screenshots."
echo "After each screenshot, press CTRL+C in the browser, then continue here."
echo ""
read -p "Press Enter to start..."

# Array of screenshots with their marker files
# Note: Paths are relative to repo root
REPO_ROOT="/root/luna-personal-assistant"
declare -a screenshots=(
  "1:Hub Home Dashboard:docs/tutorial_screenshots/core/hub_home_dashboard.png:docs/annotation_tools/markers/hub_home_markers.json"
  "2:Addon Store Browse:docs/tutorial_screenshots/core/addon_store_browse.png:docs/annotation_tools/markers/addon_store_markers.json"
  "3:Addon Store Configure:docs/tutorial_screenshots/core/addon_store_configure_extension.png:docs/annotation_tools/markers/addon_store_configure_markers.json"
  "4:Tool/MCP Manager:docs/tutorial_screenshots/core/tool_mcp_manager.png:docs/annotation_tools/markers/tool_mcp_manager_markers.json"
  "5:Key Manager:docs/tutorial_screenshots/core/key_manager_secrets.png:docs/annotation_tools/markers/key_manager_markers.json"
  "6:Infrastructure:docs/tutorial_screenshots/core/infrastructure_external_services.png:docs/annotation_tools/markers/infrastructure_markers.json"
  "7:Extension Manager:docs/tutorial_screenshots/core/extension_manager.png:docs/annotation_tools/markers/extension_manager_markers.json"
  "8:Memories Tab:docs/tutorial_screenshots/automation_memory/memories_tab.png:docs/annotation_tools/markers/automation_memory_markers.json"
  "9:Task Flows Tab:docs/tutorial_screenshots/automation_memory/task_flows_tab.png:docs/annotation_tools/markers/task_flows_markers.json"
  "10:Scheduled Tasks:docs/tutorial_screenshots/automation_memory/scheduled_tasks_tab.png:docs/annotation_tools/markers/scheduled_tasks_markers.json"
  "11:Walmart Manager:docs/tutorial_screenshots/chefbyte/walmart_manager.png:docs/annotation_tools/markers/walmart_manager_markers.json"
  "12:Recipe Browser:docs/tutorial_screenshots/chefbyte/recipe_browser.png:docs/annotation_tools/markers/recipe_browser_markers.json"
  "13:Scanner (With Items):docs/tutorial_screenshots/chefbyte/scanner_io_wizard_with_items.png:docs/annotation_tools/markers/scanner_markers.json"
  "14:Quick Chat:docs/tutorial_screenshots/quick_chat_interface.png:docs/annotation_tools/markers/quick_chat_markers.json"
)

total=${#screenshots[@]}
completed=0

for item in "${screenshots[@]}"; do
  IFS=':' read -r num name image markers <<< "$item"

  echo ""
  echo "========================================="
  echo "Screenshot $num of $total: $name"
  echo "========================================="

  # Check if marker file has any markers
  image_path="$REPO_ROOT/$image"
  marker_path="$REPO_ROOT/$markers"
  if [ ! -f "$marker_path" ]; then
    echo "⚠ Marker file not found: $marker_path"
    marker_count=0
  else
    marker_count=$(jq 'length' "$marker_path" 2>/dev/null || echo "0")
  fi
  if [ "$marker_count" = "0" ]; then
    echo "⊘ No markers defined - skipping (visual reference only)"
    ((completed++))
    continue
  fi

  # Check if already annotated
  filename=$(basename "$image")
  json_file="$REPO_ROOT/docs/tutorial_screenshots/annotated/${filename%.*}_annotations.json"

  if [ -f "$json_file" ]; then
    echo "✓ Already annotated: $json_file"
    read -p "Skip this one? (y/n): " skip
    if [ "$skip" = "y" ]; then
      echo "Skipping..."
      ((completed++))
      continue
    fi
  fi

  echo "Image: $image_path"
  echo "Markers: $marker_path ($marker_count markers)"
  echo ""
  echo "Starting annotation tool..."
  echo "Open: http://192.168.0.166:5555"
  echo ""
  echo "When done:"
  echo "  1. Drag all markers to their positions"
  echo "  2. Click 'Done - Save Annotation'"
  echo "  3. Press CTRL+C here to continue to next screenshot"
  echo ""

  # Run annotation tool (will block until user kills it)
  cd "$REPO_ROOT" && .venv/bin/python3 docs/annotation_tools/annotate_web.py "$image_path" "$marker_path"

  # Check if annotation was saved
  if [ -f "$json_file" ]; then
    echo ""
    echo "✓ Saved: $json_file"
    ((completed++))
  else
    echo ""
    echo "⚠ Warning: Annotation not found. Did you click Save?"
    read -p "Mark as completed anyway? (y/n): " mark_done
    if [ "$mark_done" = "y" ]; then
      ((completed++))
    fi
  fi

  echo ""
  read -p "Press Enter to continue to next screenshot (or type 'quit' to stop): " continue_choice
  if [ "$continue_choice" = "quit" ]; then
    echo "Stopping annotation session..."
    break
  fi
done

echo ""
echo "========================================="
echo "Annotation Session Complete!"
echo "========================================="
echo "Completed: $completed of $total screenshots"
echo ""
echo "Next steps:"
echo "  1. Review annotated images in docs/tutorial_screenshots/annotated/"
echo "  2. Generate documentation: .venv/bin/python3 docs/annotation_tools/generate_docs.py"
echo "  3. Edit generated Markdown files"
echo ""
