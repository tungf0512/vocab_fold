# FoldLex definition coverage

This report is generated from `data/definitions.json`. A row is counted
as verified only when its definition is directly sourced from an approved
lexical source or the original curated FoldLex text; morphology-derived
forms are tracked separately.

| Metric | Count | Percent |
|---|---:|---:|
| Total vocabulary entries | 100,000 | 100.0000% |
| Valid lexical entries with any local definition | 97,760 | 97.7600% |
| Verified definitions | 97,623 | 97.6230% |
| Morphology-generated definitions | 137 | 0.1370% |
| Model-generated definitions | 0 | 0.0000% |
| Needs manual review | 2,240 | 2.2400% |
| Unresolved meanings | 2,240 | 2.2400% |

## Sources

- `foldlex-curated`: 514
- `gcide-0.53`: 113
- `open-english-wordnet-2025-plus`: 48,502
- `open-english-wordnet-2025-plus+morphology`: 128
- `unresolved`: 2,240
- `wiktionary-kaikki-english`: 48,494
- `wiktionary-kaikki-english+morphology`: 9

## Interpretation

- Band values are estimated study difficulty buckets, not official IELTS word ratings.
- Unresolved rows are not assigned a placeholder meaning.
- `data/definitions.json` retains source, confidence, and morphology provenance per record.
