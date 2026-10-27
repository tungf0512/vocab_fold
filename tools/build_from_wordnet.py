#!/usr/bin/env python3
"""Compatibility entry point for the canonical FoldLex offline builder.

The old utility replaced the preserved word list with arbitrary WordNet rows.
That behavior is intentionally retired. This wrapper forwards to the new
pipeline, which preserves all 100,000 canonical IDs and reports unresolved
entries honestly.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_offline_database import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

