#!/usr/bin/env bash
# Render white/gray/black previews for a layout config.
# Usage: westfab-previews/render_preview.sh westfab-previews/layouts/WF-GF-4X4.json [color ...]
set -euo pipefail

BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
SCRIPT="$(cd "$(dirname "$0")" && pwd)/render_layout.py"
CONFIG="${1:?usage: render_preview.sh <layout.json> [colors...]}"
shift || true
COLORS=("$@"); [ ${#COLORS[@]} -eq 0 ] && COLORS=(white gray black)

for c in "${COLORS[@]}"; do
  echo ">> rendering $c"
  "$BLENDER" --background --python "$SCRIPT" -- --config "$CONFIG" --color "$c"
done
