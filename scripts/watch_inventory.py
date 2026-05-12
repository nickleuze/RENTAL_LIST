#!/usr/bin/env python3
"""Watch the Excel inventory workbook and rebuild catalog JSON when it changes."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_INPUT = Path(os.environ.get("INVENTORY_XLSM", "Rental-Database.xlsm"))
DEFAULT_INTERVAL = 1.0


def fingerprint(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def run_build(input_path: Path) -> bool:
    result = subprocess.run([sys.executable, "scripts/convert_inventory.py", "--input", str(input_path)], check=False)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild data/inventory.json when Rental-Database.xlsm changes")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Polling interval in seconds")
    args = parser.parse_args()

    print(f"Watching {args.input} for changes. Press Ctrl+C to stop.")
    last_seen = fingerprint(args.input)
    if last_seen is None:
        print(f"Missing input workbook: {args.input}", file=sys.stderr)
        return 1

    if not run_build(args.input):
        print("Initial build failed; watcher will continue and retry on the next change.", file=sys.stderr)

    try:
        while True:
            time.sleep(args.interval)
            current = fingerprint(args.input)
            if current is None:
                if last_seen is not None:
                    print(f"Workbook disappeared: {args.input}", file=sys.stderr)
                last_seen = None
                continue

            if current != last_seen:
                # Give Excel a moment to finish writing the file.
                time.sleep(0.25)
                last_seen = fingerprint(args.input)
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Change detected; rebuilding catalog data...")
                run_build(args.input)
    except KeyboardInterrupt:
        print("\nStopped watcher.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
