# FoldLex development notes

## Data contract

- `data/FoldLex-100000-Vocabulary.csv` is the preserved canonical word list.
- The normalized, case-folded word is the stable record ID. This is also the
  key used by the existing `foldlex-notebook-v1` progress store.
- `data/definitions.json` is the rich local dictionary artifact.
- `data/vocabulary-100k-complete.csv` is the review/export form with provenance
  and verification columns.
- `data/definitions-index.json` maps stable IDs to rows in `definitions.json`.

## Runtime contract

The UI renders only the current 16-card page (or the daily deck), not the full
dataset into the DOM. The dataset is parsed once into memory for simple local
filtering, while progress/bookmarks remain compatible with the original
localStorage schema. There is no runtime dictionary fetch.

When changing the data schema, update the builder, validator, report generator,
and `tests/test_data_pipeline.py` together. Do not add an unresolved or generic
placeholder definition merely to make a coverage percentage look higher.

## Quality gates

Run the complete checks before packaging:

```bash
python scripts/validate_definitions.py
python scripts/report_coverage.py
python -m unittest discover -s tests -p 'test_*.py'
```

Inspect `reports/unresolved-words.csv` and the samples in
`reports/quality-audit.md` before claiming verified coverage.

