#!/usr/bin/env python3
"""Run the rental catalog dev server and auto-rebuild inventory data.

This is intended for Docker/local development: one process serves the static site
while a background thread watches Rental-Database.xlsm and regenerates
 data/inventory.json after saves.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

DEFAULT_INPUT = Path(os.environ.get("INVENTORY_XLSM", "Rental-Database.xlsm"))
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
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


def watch_inventory(input_path: Path, interval: float) -> None:
    last_seen = fingerprint(input_path)
    if last_seen is None:
        print(f"Missing input workbook: {input_path}", file=sys.stderr, flush=True)
    else:
        print(f"Watching {input_path} for changes.", flush=True)

    while True:
        time.sleep(interval)
        current = fingerprint(input_path)
        if current is None:
            if last_seen is not None:
                print(f"Workbook disappeared: {input_path}", file=sys.stderr, flush=True)
            last_seen = None
            continue

        if current != last_seen:
            # Give Excel a moment to finish writing the file.
            time.sleep(0.25)
            last_seen = fingerprint(input_path)
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] Change detected; rebuilding catalog data...", flush=True)
            run_build(input_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve catalog and rebuild inventory JSON when Excel changes")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    args = parser.parse_args()

    run_build(args.input)

    watcher = threading.Thread(target=watch_inventory, args=(args.input, args.interval), daemon=True)
    watcher.start()

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=".")
    server = http.server.ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving rental catalog at http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped dev server.", flush=True)
        return 0
    finally:
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
