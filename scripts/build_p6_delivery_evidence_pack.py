"""Build the P6 delivery evidence pack."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from pcdad.analysis.delivery_evidence import (
    build_default_delivery_evidence_records,
    render_delivery_evidence_markdown,
    render_final_delivery_report_draft,
    write_delivery_evidence_csv,
)

DEFAULT_OUTPUT_CSV = Path("docs/document/stage_record/2026-06-14_p6_delivery_evidence_index.csv")
DEFAULT_OUTPUT_MD = Path("docs/document/stage_record/2026-06-14_p6_delivery_evidence_pack.md")
DEFAULT_REPORT_DRAFT = Path("docs/document/report/2026-06-14_final_delivery_report_draft.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--commit-hash", default="")
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--report-draft", type=Path, default=DEFAULT_REPORT_DRAFT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    commit_hash = args.commit_hash or _current_commit_hash(repo_root)
    records = build_default_delivery_evidence_records(
        repo_root=repo_root,
        commit_hash=commit_hash,
    )

    csv_path = write_delivery_evidence_csv(records, args.output_csv)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_delivery_evidence_markdown(records), encoding="utf-8")
    args.report_draft.parent.mkdir(parents=True, exist_ok=True)
    args.report_draft.write_text(render_final_delivery_report_draft(records), encoding="utf-8")

    print(f"Wrote delivery evidence CSV to {csv_path}")
    print(f"Wrote delivery evidence markdown to {args.output_md}")
    print(f"Wrote final report draft to {args.report_draft}")
    print(f"Processed {len(records)} evidence records")


def _current_commit_hash(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


if __name__ == "__main__":
    main()
