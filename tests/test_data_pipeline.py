from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FoldLexReleaseTests(unittest.TestCase):
    def test_canonical_vocabulary_has_100k_unique_ids(self):
        import csv

        with (ROOT / "data/FoldLex-100000-Vocabulary.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 100_000)
        ids = [row["Word"].strip().casefold() for row in rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_local_definition_artifact_is_structurally_complete(self):
        path = ROOT / "data/definitions.json"
        if not path.exists():
            self.skipTest("run scripts/build_offline_database.py first")
        rows = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 100_000)
        self.assertEqual(len({row["id"] for row in rows}), 100_000)
        self.assertTrue(all("source" in row and "confidence" in row for row in rows))

    def test_release_has_no_runtime_dictionary_fetch(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        runtime = re.search(r"<script>(.*?)</script>", html, re.S)
        self.assertIsNotNone(runtime)
        self.assertNotIn("api.dictionaryapi.dev", runtime.group(1))
        self.assertNotIn("fetch(", runtime.group(1))

    def test_learning_modes_and_progress_key_are_present(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for expected in ("Morning Reading", "Folded Recall", "foldlex-notebook-v1", "Got it", "Again", "Save"):
            self.assertIn(expected, html)


if __name__ == "__main__":
    unittest.main()

