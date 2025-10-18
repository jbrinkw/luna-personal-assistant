#!/bin/bash
# Fix node_modules .bin permissions issue
#
# PROBLEM: npm install on some systems doesn't set execute permissions on
# binaries in node_modules/.bin/, causing "Permission denied" errors when
# running vite, eslint, etc.
#
# This is a WORKAROUND script. See BETTER SOLUTIONS below.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Fixing node_modules/.bin permissions..."

# Fix hub_ui
if [ -d "$PROJECT_ROOT/hub_ui/node_modules/.bin" ]; then
    chmod +x "$PROJECT_ROOT/hub_ui/node_modules/.bin/"* 2>/dev/null || true
    echo "✓ Fixed hub_ui"
fi

# Fix all extension UIs
for ext_ui in "$PROJECT_ROOT"/extensions/*/ui/node_modules/.bin; do
    if [ -d "$ext_ui" ]; then
        chmod +x "$ext_ui"/* 2>/dev/null || true
        ext_name=$(basename $(dirname $(dirname "$ext_ui")))
        echo "✓ Fixed $ext_name"
    fi
done

echo "Done!"
echo ""
echo "======================================================================"
echo "BETTER SOLUTIONS TO PREVENT THIS ISSUE:"
echo "======================================================================"
echo ""
echo "Option 1: Use pnpm instead of npm (RECOMMENDED)"
echo "  - pnpm correctly handles permissions during install"
echo "  - Faster and more disk-efficient"
echo "  - Replace 'npm install' with 'pnpm install' in:"
echo "    • core/scripts/start_all.sh (lines ~87, 110, 133)"
echo "    • Any other scripts that run npm install"
echo ""
echo "Option 2: Add post-install hook to package.json"
echo "  In each package.json, add:"
echo '  "scripts": {'
echo '    "postinstall": "chmod +x node_modules/.bin/* 2>/dev/null || true",'
echo '    ...'
echo '  }'
echo ""
echo "Option 3: Check umask and npm config"
echo "  - Current umask: $(umask)"
echo "  - npm config get umask: $(npm config get umask 2>/dev/null || echo 'not set')"
echo "  - Try: npm config set umask 0022"
echo ""
echo "Option 4: Use a container/VM with consistent permissions"
echo "  - This ensures npm install works the same for all developers"
echo ""
echo "======================================================================"




