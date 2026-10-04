#!/bin/bash
# ==============================================================================
# Regression Execution Script for or_gate
# ==============================================================================
set -e

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_DIR"

echo "=== SiliCAD / EDA_MCP Automated Regression Suite for or_gate ==="
tcsh -c "source /cadence/cshrc; python3 scripts/run_regression.py"
