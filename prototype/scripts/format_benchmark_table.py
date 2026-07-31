from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from locus.experiment_metadata import validate_experiment_metadata
from locus.redaction import validate_public_output

ROOT = Path(__file__).resolve().parents[2]


def fmt_ms(value: float) -> str:
    return f"{value:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Format LOCUS benchmark JSON as LaTeX table rows."
    )
    parser.add_argument(
        "input", type=Path, help="benchmark JSON from run_benchmarks.py"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="optional output path; parent directories are created",
    )
    parser.add_argument(
        "--cue-count",
        type=int,
        default=None,
        help="optional cue-count filter for compact paper tables",
    )
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    validate_public_output(payload)
    if args.out is not None:
        try:
            paper_relative = args.out.resolve().relative_to(
                (ROOT / "paper/generated").resolve()
            )
        except ValueError:
            paper_relative = None
        if paper_relative is not None:
            metadata = validate_experiment_metadata(payload.get("metadata"))
            if metadata["evidence_class"] != "paper":
                raise SystemExit(
                    "paper/generated output requires paper-evidence benchmark metadata"
                )
    lines = [
        "% t & n & cues & enroll median ms & recover median ms & backup B & party storage B & recovery msg B"
    ]
    for row in payload["results"]:
        if args.cue_count is not None and row["cue_count"] != args.cue_count:
            continue
        lines.append(
            " & ".join(
                [
                    str(row["threshold"]),
                    str(row["parties"]),
                    str(row["cue_count"]),
                    fmt_ms(row["enroll_time"]["median_ms"]),
                    fmt_ms(row["recover_time"]["median_ms"]),
                    f"{row['backup_bytes_mean']:.0f}",
                    f"{row['total_party_record_bytes_mean']:.0f}",
                    f"{row['recovery_message_bytes_mean']:.0f}",
                ]
            )
            + r" \\"
        )
    output = "\n".join(lines) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
