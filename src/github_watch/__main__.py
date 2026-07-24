from __future__ import annotations

from pathlib import Path
import argparse

from .monitor import run_monitor


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the GitHub-only website watcher.")
    parser.add_argument("--state", default="data/state.json", help="Path to state JSON file.")
    parser.add_argument("--screenshots", default="data/screenshots", help="Screenshot output directory.")
    args = parser.parse_args()

    return run_monitor(Path(args.state), Path(args.screenshots))


if __name__ == "__main__":
    raise SystemExit(main())
