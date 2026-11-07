#!/usr/bin/env python3
"""
Deterministic HTML Report Generator for the /analyze-paper skill.
Validates extracted JSON data against the P-M-D-M structure and renders
a standalone interactive HTML report using resources/report_template.html.
"""

import argparse
import json
import sys
from pathlib import Path


REQUIRED_TOP_KEYS = [
    "metadata",
    "problem",
    "methods",
    "datasets",
    "metrics",
    "experimental_results",
    "critical_review",
]


def validate_paper_record(record: dict, idx: int = 0) -> list[str]:
    warnings = []
    if not isinstance(record, dict):
        return [f"Record #{idx + 1} is not a JSON object."]

    for key in REQUIRED_TOP_KEYS:
        if key not in record:
            warnings.append(f"Record #{idx + 1}: Missing top-level key '{key}'.")

    meta = record.get("metadata", {})
    if not meta.get("title"):
        warnings.append(f"Record #{idx + 1}: 'metadata.title' is empty.")

    prob = record.get("problem", {})
    for pkey in ("broad_domain", "specific_task", "problem_statement", "evidence_location"):
        if not prob.get(pkey):
            warnings.append(f"Record #{idx + 1}: 'problem.{pkey}' is missing or empty.")

    meth = record.get("methods", {})
    if not meth.get("proposed_components"):
        warnings.append(f"Record #{idx + 1}: 'methods.proposed_components' is empty.")

    if not isinstance(record.get("datasets"), list):
        warnings.append(f"Record #{idx + 1}: 'datasets' should be a list.")

    if not isinstance(record.get("metrics"), list):
        warnings.append(f"Record #{idx + 1}: 'metrics' should be a list.")

    return warnings


def load_json_records(input_paths: list[str]) -> list[dict]:
    records = []
    for p_str in input_paths:
        path = Path(p_str)
        if not path.exists():
            raise FileNotFoundError(f"Input JSON file not found: {path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            records.extend(raw)
        elif isinstance(raw, dict) and "papers" in raw and isinstance(raw["papers"], list):
            records.extend(raw["papers"])
        elif isinstance(raw, dict):
            records.append(raw)
        else:
            raise ValueError(f"Unsupported JSON root structure in {path}")
    return records


def build_html(records: list[dict], template_path: Path) -> str:
    if not template_path.exists():
        raise FileNotFoundError(f"HTML template not found at: {template_path}")

    template_html = template_path.read_text(encoding="utf-8")
    if len(records) == 1:
        report_title = records[0].get("metadata", {}).get("title", "Paper Analysis")
        payload = records[0]
    else:
        report_title = f"Comparison of {len(records)} Research Papers"
        payload = records

    # Prevent accidental </script> tag termination inside embedded JSON
    safe_json = json.dumps(payload, indent=2, ensure_ascii=False).replace("</", "<\\/")

    rendered = template_html.replace("{{REPORT_TITLE}}", str(report_title))
    rendered = rendered.replace("{{PAPER_DATA_JSON}}", safe_json)
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an interactive HTML paper classification report from extracted JSON."
    )
    parser.add_argument(
        "--input",
        "-i",
        nargs="+",
        required=True,
        help="Path(s) to extracted paper analysis JSON file(s). Pass multiple files for multi-paper comparison mode.",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output path for the generated .html report.",
    )
    parser.add_argument(
        "--template",
        "-t",
        default=None,
        help="Optional custom HTML template path (defaults to ../resources/report_template.html).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero code if validation warnings are found.",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    default_template = script_dir.parent / "resources" / "report_template.html"
    template_path = Path(args.template) if args.template else default_template

    try:
        records = load_json_records(args.input)
    except Exception as exc:
        print(f"[ERROR] Failed to load input JSON: {exc}", file=sys.stderr)
        return 1

    all_warnings = []
    for idx, rec in enumerate(records):
        all_warnings.extend(validate_paper_record(rec, idx))

    if all_warnings:
        print("[VALIDATION WARNINGS]", file=sys.stderr)
        for w in all_warnings:
            print(f"  - {w}", file=sys.stderr)
        if args.strict:
            return 2

    try:
        html_content = build_html(records, template_path)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html_content, encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "success",
                    "papers_processed": len(records),
                    "warnings_count": len(all_warnings),
                    "output_html": str(out_path.resolve()),
                },
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(f"[ERROR] Failed to generate HTML report: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

