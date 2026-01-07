#!/usr/bin/env python3
"""Simple file watcher that watches .py files in the project."""

import subprocess
import sys
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_DIRS = [".", "MCCReader"]


class PyFileHandler(FileSystemEventHandler):
    def __init__(self, script):
        self.script = script
        self.process = None
        self.last_restart = 0
        self.debounce_seconds = 1
        self.start_script()

    def start_script(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        print(f"\n{'=' * 50}")
        print(f"▶ Running: python {self.script}")
        print("=" * 50)
        self.process = subprocess.Popen([sys.executable, self.script])

    def should_restart(self, path):
        # Only watch .py files
        p = Path(path)
        if p.suffix != ".py":
            return False
        # Exclude watch.py itself
        if p.name == "watch.py":
            return False
        # Debounce
        now = time.time()
        if now - self.last_restart < self.debounce_seconds:
            return False
        self.last_restart = now
        return True

    def on_modified(self, event):
        if not event.is_directory and self.should_restart(event.src_path):
            print(f"\n🔄 File changed: {event.src_path}")
            self.start_script()


if __name__ == "__main__":
    print("🔥 Hot reload enabled - watching for changes...")
    print(f"   Watching: {', '.join(WATCH_DIRS)}")
    print("   Press Ctrl+C to stop\n")

    handler = PyFileHandler("dev.py")
    observer = Observer()
    for watch_dir in WATCH_DIRS:
        observer.schedule(handler, watch_dir, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if handler.process:
            handler.process.terminate()
    observer.join()
