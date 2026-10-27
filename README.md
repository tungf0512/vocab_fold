# FoldLex — IELTS Vocabulary Notebook

FoldLex is an offline-first two-column vocabulary notebook with Morning Reading,
Folded Recall, estimated learning bands, search, bookmarks, difficult-word
review, spaced repetition, CSV import/export, and local progress storage.

## Current build status

The preserved canonical list contains exactly 100,000 case-insensitive unique
entries. This release packages 97,760 local English explanations and reports
2,240 entries with no approved lexical evidence. Verified coverage is 97,623
entries (97.6230%); 137 additional entries are explicitly marked as
morphology-generated from a verified lemma. No model-generated or generic
placeholder definitions are included.

The unresolved entries are not hidden: see
[`reports/unresolved-words.csv`](reports/unresolved-words.csv) and
[`reports/coverage.md`](reports/coverage.md). They include abbreviations,
typo-like strings, Roman numerals, proper-noun-like items, and rare or obsolete
forms that the approved sources did not verify. The project therefore does not
claim 100% verified lexical coverage.

## Run the website offline

Open [`index.html`](index.html) directly after downloading the project. The
standalone HTML embeds the vocabulary and definitions, so the learning workflow
does not depend on a network dictionary service. If a browser restricts local
storage for `file://`, run:

```bash
python -m http.server 8000
```

and open <http://localhost:8000/>. Only the current page/daily deck is rendered
into the DOM; the full dataset is held as local data for efficient filtering.

## Data artifacts

- `data/FoldLex-100000-Vocabulary.csv` — preserved canonical list and original
  columns.
- `data/definitions.json` — rich local dictionary records with primary and
  additional senses, examples where available, part of speech, source,
  confidence, verification, and morphology provenance.
- `data/definitions-index.json` — stable ID to row index map.
- `data/vocabulary-100k-complete.csv` — review/export CSV with provenance fields.
- `data/metadata.json` — schema, license, and build metrics.

The normalized, case-folded word is the stable record ID, preserving compatibility
with the existing `foldlex-notebook-v1` progress/bookmark store.

## Rebuild the dictionary

The reproducible pipeline downloads open sources into `.cache/`, not the release
package:

```bash
python scripts/download_sources.py --output-dir .cache/foldlex-sources
python scripts/build_offline_database.py
python scripts/report_coverage.py
python scripts/validate_definitions.py
python -m unittest discover -s tests -p 'test_*.py'
python scripts/package_release.py
```

The normal build fails if an entry has no approved evidence. Use
`--allow-unresolved` only to produce an honest investigative build and review
the resulting exception report. Builds are UTF-8, deterministic apart from the
recorded build date, and safe to rerun.

## Sources and licensing

The merge uses Open English WordNet 2025+ (CC BY 4.0), English Wiktionary via
Kaikki (CC BY-SA 4.0), optional GCIDE 0.53 (GPLv3-or-later), the original
FoldLex curated explanations, and SCOWL/Hunspell only for licensed morphology
links. Full attribution and redistribution notes are in
[`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) and [`LICENSES/`](LICENSES/).

## Quality and limitations

[`reports/quality-audit.md`](reports/quality-audit.md) contains a deterministic
sample spanning common, advanced, technical, compound, inflected, and
proper-noun-like entries. Definitions are English lexical explanations, not
official IELTS or CEFR labels. The 4.0–9.0 bands are study-oriented estimates.

See [`docs/OFFLINE_SETUP.md`](docs/OFFLINE_SETUP.md) for rebuild instructions
and [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for the data/runtime contract.

