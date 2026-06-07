"""Prepare datasets and compute dataset statistics."""

from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stat", action="store_true", help="Compute dataset statistics.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.stat:
        raise SystemExit("Dataset statistics are implemented in P2 after data paths are confirmed.")
    raise SystemExit("No action requested. Use --stat after P2 is implemented.")


if __name__ == "__main__":
    main()
