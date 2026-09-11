#!/usr/bin/env bash
set -e

SOURCE_DIR="/Users/vs/function/EDA_MCP"
DEST="${1:-.}"

TARGET_DIR="$(mkdir -p "$DEST" && cd "$DEST" && pwd)"

if [ "$TARGET_DIR" = "$SOURCE_DIR" ]; then
  echo "Error: Cannot set up workspace inside the source directory ($SOURCE_DIR)." >&2
  exit 1
fi

mkdir -p "$TARGET_DIR/context"
cp -r "$SOURCE_DIR/context/designer" "$TARGET_DIR/context/"
cp -r "$SOURCE_DIR/.agents" "$TARGET_DIR/"

echo "Agent workspace ready at: $TARGET_DIR"
