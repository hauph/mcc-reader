#!/bin/bash
# Development script - runs code with live-mounted source files
# No rebuild needed after code changes!

# Usage:
#   ./dev.sh              - Run dev.py once
#   ./dev.sh --watch      - Watch mode: auto-reload on file changes
#   ./dev.sh src/other.py - Run specific script once
#   ./dev.sh --watch src/other.py - Watch mode with specific script

if [[ "$1" == "--watch" || "$1" == "-w" ]]; then
    SCRIPT="${2:-dev.py}"
    echo "🔥 Hot reload enabled - watching for changes..."
    echo "   Running: $SCRIPT"
    echo "   Press Ctrl+C to stop"
    echo ""
    # Use -t only if running in a terminal
    TTY_FLAG=""
    if [ -t 0 ]; then
        TTY_FLAG="-it"
    fi
    docker run --rm $TTY_FLAG -v "$(pwd)":/app mcc-reader \
        python watch.py "$SCRIPT"
else
    docker run --rm -v "$(pwd)":/app mcc-reader python "${@:-dev.py}"
fi

