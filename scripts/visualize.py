"""Generate anomaly heatmap visualizations."""

from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to an experiment YAML config.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raise SystemExit(f"Visualization entrypoint is implemented in P3/P4. Config: {args.config}")


if __name__ == "__main__":
    main()
