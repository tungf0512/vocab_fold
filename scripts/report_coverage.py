#!/usr/bin/env python3
"""Write human-readable coverage and deterministic quality-audit reports."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_rows(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_reports(rows: list[dict], reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    total = len(rows)
    defined = [row for row in rows if row.get("definition")]
    verified = [row for row in rows if row.get("verified")]
    generated = [row for row in rows if row.get("generated")]
    unresolved = [row for row in rows if not row.get("definition")]
    source_counts = defaultdict(int)
    confidence_counts = defaultdict(int)
    for row in rows:
        source_counts[row.get("source", "")] += 1
        confidence_counts[row.get("confidence", "")] += 1

    coverage = {
        "total_vocabulary_entries": total,
        "valid_lexical_entries": len(defined),
        "entries_with_verified_definitions": len(verified),
        "entries_with_model_generated_definitions": 0,
        "entries_with_morphology_generated_definitions": len(generated),
        "entries_needing_manual_review": sum(row.get("confidence") == "low" or not row.get("definition") for row in rows),
        "entries_with_unresolved_meanings": len(unresolved),
        "overall_definition_coverage_percent": round(100 * len(defined) / total, 4) if total else 0,
        "verified_definition_coverage_percent": round(100 * len(verified) / total, 4) if total else 0,
        "source_counts": dict(sorted(source_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
    }
    (reports_dir / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# FoldLex definition coverage",
        "",
        "This report is generated from `data/definitions.json`. A row is counted",
        "as verified only when its definition is directly sourced from an approved",
        "lexical source or the original curated FoldLex text; morphology-derived",
        "forms are tracked separately.",
        "",
        "| Metric | Count | Percent |",
        "|---|---:|---:|",
        f"| Total vocabulary entries | {total:,} | 100.0000% |",
        f"| Valid lexical entries with any local definition | {len(defined):,} | {coverage['overall_definition_coverage_percent']:.4f}% |",
        f"| Verified definitions | {len(verified):,} | {coverage['verified_definition_coverage_percent']:.4f}% |",
        f"| Morphology-generated definitions | {len(generated):,} | {100 * len(generated) / total:.4f}% |" if total else "| Morphology-generated definitions | 0 | 0.0000% |",
        "| Model-generated definitions | 0 | 0.0000% |",
        f"| Needs manual review | {coverage['entries_needing_manual_review']:,} | {100 * coverage['entries_needing_manual_review'] / total:.4f}% |" if total else "| Needs manual review | 0 | 0.0000% |",
        f"| Unresolved meanings | {len(unresolved):,} | {100 * len(unresolved) / total:.4f}% |" if total else "| Unresolved meanings | 0 | 0.0000% |",
        "",
        "## Sources",
        "",
    ]
    for source, count in sorted(source_counts.items()):
        lines.append(f"- `{source or 'missing'}`: {count:,}")
    lines.extend(["", "## Interpretation", "", "- Band values are estimated study difficulty buckets, not official IELTS word ratings.", "- Unresolved rows are not assigned a placeholder meaning.", "- `data/definitions.json` retains source, confidence, and morphology provenance per record.", ""])
    (reports_dir / "coverage.md").write_text("\n".join(lines), encoding="utf-8")

    with (reports_dir / "unresolved-words.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["word", "id", "band", "topic", "reason"])
        for row in unresolved:
            writer.writerow([row.get("word", ""), row.get("id", ""), row.get("band", ""), row.get("topic", ""), row.get("unresolved_reason", "Manual lexical review required")])

    # Stable, reviewable sample covering the requested edge classes.
    groups = {
        "common": lambda row: row.get("band") == 4,
        "advanced": lambda row: row.get("band") == 9,
        "rare_or_wiktionary": lambda row: row.get("source") in {"wiktionary-kaikki-english", "gcide-0.53"} and row.get("band", 0) >= 8,
        "technical": lambda row: any(token in row.get("topic", "").casefold() for token in ("science", "technology")),
        "compound": lambda row: " " in row.get("word", "") or "-" in row.get("word", ""),
        "inflection": lambda row: bool(row.get("generated")),
        "proper_noun_like": lambda row: row.get("part_of_speech") == "proper noun" or row.get("word", "").casefold() in {"aaliyah", "abbott", "napoleon"},
    }
    used: set[str] = set()
    audit_lines = [
        "# FoldLex definition quality-audit sample",
        "",
        "This deterministic sample is generated for human review. It covers common, advanced, rare/source-diverse, technical, compound, inflected, and proper-noun-like entries.",
        "",
    ]
    for name, predicate in groups.items():
        selected = []
        for row in rows:
            if row.get("id") in used or not row.get("definition") or not predicate(row):
                continue
            selected.append(row)
            used.add(row.get("id"))
            if len(selected) >= 5:
                break
        audit_lines.extend([f"## {name}", ""])
        if not selected:
            audit_lines.append("No defined rows matched this category in the current build.")
        for row in selected:
            extra = ""
            if len(row.get("senses", [])) > 1:
                extra = "\n  - Additional senses: " + " | ".join(row["senses"][1:])
            audit_lines.extend([
                f"- **{row['word']}** — {row['definition']}",
                f"  - POS: {row.get('part_of_speech', 'unknown')}; source: `{row.get('source')}`; confidence: `{row.get('confidence')}`; generated: `{row.get('generated')}`" + extra,
            ])
        audit_lines.append("")
    (reports_dir / "quality-audit.md").write_text("\n".join(audit_lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--definitions", type=Path, default=ROOT / "data/definitions.json")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    write_reports(load_rows(args.definitions), args.reports_dir)
    print(f"Wrote reports to {args.reports_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

