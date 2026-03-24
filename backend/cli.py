from __future__ import annotations

import argparse

from .service import EEGService


def main() -> None:
    parser = argparse.ArgumentParser(description="EEG library tooling")
    parser.add_argument("command", choices=["reindex"], help="Command to run")
    args = parser.parse_args()

    service = EEGService()
    if args.command == "reindex":
        result = service.reindex()
        print(f"Scanned: {result.scanned}, inserted/updated: {result.inserted_or_updated}")


if __name__ == "__main__":
    main()
