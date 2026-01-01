#!/bin/bash

# File Monitor Interactive Menu Launcher
# Launches the interactive TUI menu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Starting File Monitor Interactive Mode..."
echo "Use arrow keys to navigate and Enter to select"
echo ""

python3 src/interactive_menu.py
