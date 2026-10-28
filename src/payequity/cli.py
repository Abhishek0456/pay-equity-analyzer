"""Command-line entry point.

Planned commands (Part 8/9):
    python -m payequity generate --scale starter|full [--seed N] [--out output/]
    python -m payequity analyze  --scale starter|full
    python -m payequity validate --scale starter|full
    python -m payequity reproduce --scale starter     # run twice, compare checksums
    python -m payequity all      --scale starter      # generate -> analyze -> validate -> export
"""

import argparse
from pathlib import Path

from payequity.pipeline import analyze, build_review_workflow, export_outputs, generate, validate
from payequity.reproducibility import verify_reproducible
from payequity.validation.checks import validate_tables
from payequity.validation.report import write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="payequity", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("generate", "analyze", "validate", "reproduce", "all"):
        p = sub.add_parser(name)
        p.add_argument("--scale", choices=["starter", "full"], default="starter")
        p.add_argument("--seed", type=int, default=None, help="override config seed")
        p.add_argument("--out", default="output", help="output root directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "reproduce":
        ok = verify_reproducible(generate, args.scale, args.seed)
        print("reproducible" if ok else "not reproducible")
        return 0 if ok else 1
    tables = generate(scale=args.scale, seed=args.seed)
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(output / f"{name}.csv", index=False)
    if args.command == "all":
        analytics = analyze(tables)
        workflow = build_review_workflow(analytics, 2026, "EMP-000001")
        combined = {**tables, **analytics, **workflow}
        errors = validate(tables)
        if errors:
            write_report(errors, output / "validation_summary.json")
            return 1
        export_outputs(combined, output)
        print(f"wrote {len(combined)} end-to-end tables")
        return 0
    if args.command == "analyze":
        analytics = analyze(tables)
        for name, frame in analytics.items():
            frame.to_csv(output / f"{name}.csv", index=False)
        print(f"wrote {len(analytics)} analytics tables")
        return 0
    if args.command in {"validate", "all"}:
        errors = validate_tables(tables)
        write_report(errors, output / "validation_summary.json")
        if errors:
            return 1
    return 0
