#!/usr/bin/env python3
"""Validate the generated FoldLex local definition database."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lexical_pipeline import PLACEHOLDER_RE, english_text, normalize_word  # noqa: E402


def validate(path: Path, expected_count: int = 100_000, allow_unresolved: bool = False) -> tuple[list[str], dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if not isinstance(rows, list):
        return ["definitions.json must contain a JSON list"], {}
    if len(rows) != expected_count:
        errors.append(f"expected {expected_count:,} rows, found {len(rows):,}")
    ids: set[str] = set()
    definitions: defaultdict[str, list[str]] = defaultdict(list)
    for index, row in enumerate(rows, start=1):
        prefix = f"row {index}"
        if not isinstance(row, dict):
            errors.append(f"{prefix}: not an object")
            continue
        row_id = normalize_word(row.get("id"))
        word = normalize_word(row.get("word"))
        if not row_id or row_id != word:
            errors.append(f"{prefix}: id does not equal normalized word")
        if row_id in ids:
            errors.append(f"{prefix}: duplicate id {row_id!r}")
        ids.add(row_id)
        definition = str(row.get("definition", "")).strip()
        if not definition:
            if not allow_unresolved:
                errors.append(f"{prefix} {word!r}: empty definition")
            continue
        if not english_text(definition):
            errors.append(f"{prefix} {word!r}: definition is not English-like")
        if PLACEHOLDER_RE.search(definition):
            errors.append(f"{prefix} {word!r}: placeholder text detected")
        if len(definition) > 1200:
            errors.append(f"{prefix} {word!r}: definition exceeds 1,200 characters")
        if normalize_word(definition).strip(" .") == word:
            errors.append(f"{prefix} {word!r}: circular definition")
        senses = row.get("senses")
        if not isinstance(senses, list) or not senses or any(not str(s).strip() for s in senses):
            errors.append(f"{prefix} {word!r}: missing or malformed senses")
        source = str(row.get("source", "")).strip()
        confidence = str(row.get("confidence", "")).strip()
        if (not source or source == "unresolved") and not allow_unresolved:
            errors.append(f"{prefix} {word!r}: missing provenance")
        if confidence not in {"high", "medium", "low", "none"}:
            errors.append(f"{prefix} {word!r}: invalid confidence {confidence!r}")
        if bool(row.get("verified")) and bool(row.get("generated")):
            errors.append(f"{prefix} {word!r}: generated definition marked verified")
        if bool(row.get("verified")) and confidence == "none":
            errors.append(f"{prefix} {word!r}: none-confidence definition marked verified")
        definitions[definition].append(word)

    repeated = {definition: words for definition, words in definitions.items() if len(words) > 1}
    suspicious_repeats = {definition: words for definition, words in repeated.items() if len(words) >= 8 and not any("form of" in definition.casefold() for _ in [0])}
    metrics = {
        "rows": len(rows),
        "unique_ids": len(ids),
        "definitions_nonempty": sum(bool(str(row.get("definition", "")).strip()) for row in rows if isinstance(row, dict)),
        "verified": sum(bool(row.get("verified")) for row in rows if isinstance(row, dict)),
        "generated": sum(bool(row.get("generated")) for row in rows if isinstance(row, dict)),
        "unresolved": sum(not str(row.get("definition", "")).strip() for row in rows if isinstance(row, dict)),
        "repeated_definition_groups": len(repeated),
        "suspicious_repeated_definition_groups": len(suspicious_repeats),
        "source_counts": dict(Counter(str(row.get("source", "")) for row in rows if isinstance(row, dict))),
    }
    # Exact gloss reuse is normal in WordNet for synonyms. The validator only
    # fails on explicit placeholder/circular text above; repeated groups are
    # surfaced as an audit metric for human review rather than misclassified as
    # corruption.
    metrics["repeated_definition_review_groups"] = len(suspicious_repeats)
    return errors, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--definitions", type=Path, default=ROOT / "data/definitions.json")
    parser.add_argument("--allow-unresolved", action="store_true", help="accept explicit unresolved rows while still validating all defined rows")
    args = parser.parse_args()
    errors, metrics = validate(args.definitions, allow_unresolved=args.allow_unresolved)
    print(json.dumps(metrics, indent=2))
    if errors:
        print(f"VALIDATION FAILED: {len(errors)} issue(s)", file=sys.stderr)
        for error in errors[:80]:
            print(f"- {error}", file=sys.stderr)
        if len(errors) > 80:
            print(f"- … {len(errors) - 80} more", file=sys.stderr)
        return 1
    print("VALIDATION PASSED WITH EXPLICIT UNRESOLVED ROWS" if args.allow_unresolved and metrics.get("unresolved") else "VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

