#!/bin/bash
# Development script - runs code with live-mounted source files
# No rebuild needed after code changes!

# Usage:
#   ./dev.sh              - Run dev.py once
#   ./dev.sh --watch      - Watch mode: auto-reload on Python file changes (except watch.py)

if [[ "$1" == "--watch" || "$1" == "-w" ]]; then
    # Use -t only if running in a terminal
    TTY_FLAG=""
    if [ -t 0 ]; then
        TTY_FLAG="-it"
    fi
    docker run --rm $TTY_FLAG -v "$(pwd)":/app mcc-reader \
        python watch.py
else
    docker run --rm -v "$(pwd)":/app mcc-reader python dev.py
fi

