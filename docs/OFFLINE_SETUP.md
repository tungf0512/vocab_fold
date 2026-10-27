# Offline setup

## Use the packaged application

The root `index.html` is the standalone distribution. It embeds the generated
vocabulary and definitions, so it can be opened after disconnecting from the
Internet. Morning Reading, Folded Recall, bookmarks, difficult-word review,
search, band/topic filters, CSV import/export, and local progress continue to
work offline.

If a browser restricts local storage for `file://`, run a local server from the
release directory:

```bash
python -m http.server 8000
```

Then open <http://localhost:8000/>. No external network access is required.

## Rebuild the local dictionary

Raw source archives stay outside the release data directory:

```bash
python scripts/download_sources.py --output-dir .cache/foldlex-sources
python scripts/build_offline_database.py
python scripts/report_coverage.py
python scripts/validate_definitions.py
python -m unittest discover -s tests -p 'test_*.py'
python scripts/package_release.py
```

The builder is restartable and idempotent. If an archive download is
interrupted, the `.part` file is retained for a future retry. Use
`--allow-unresolved` only when you need an honest partial build for investigation;
the normal release build fails rather than labeling unsupported words as
complete.

## Build inputs

The builder accepts explicit paths for each source, which makes offline or
air-gapped regeneration possible after the archives have been obtained:

```bash
python scripts/build_offline_database.py \
  --wordnet /path/to/english-wordnet-2025-plus.xml.gz \
  --wiktionary /path/to/kaikki-English.jsonl.gz \
  --gcide /path/to/gcide-0.53 \
  --hunspell-aff /usr/share/hunspell/en_US.aff \
  --hunspell-dic /usr/share/hunspell/en_US.dic
```

