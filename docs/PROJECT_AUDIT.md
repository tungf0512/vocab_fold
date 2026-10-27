# FoldLex project audit — 2026-10-27

## Repository and canonical data

- The repository is a standalone static website with the main entry point at
  `index.html`.
- The canonical 100K vocabulary file is
  `data/FoldLex-100000-Vocabulary.csv`.
- The CSV has 100,000 data rows, the columns `Word`, `Explanation`, `Band`,
  and `Topic`, and 100,000 case-insensitive unique words.
- The existing HTML embeds the same collection in two JSON script blocks:
  `seed-data` (514 curated rows) and `bulk-data` (99,486 rows). The existing
  application treats the normalized word as its record identity; no explicit
  stable ID column is currently shipped.

## Existing definition state

- The CSV contains 632 non-empty English explanations: 514 curated entries and
  118 morphology-derived notes.
- The HTML has the same definition coverage: 514 entries in `seed-data` and
  118 four-field entries in `bulk-data`.
- Definition-less rows are explicitly treated as online-lookup candidates.
  The current browser code calls `https://api.dictionaryapi.dev/...` when a
  visible row has no bundled definition and caches the result in IndexedDB.
- This online path is not suitable for the required final offline release and
  will be removed or disabled from the release build.

## Existing learning application

- The two-column paper UI, Morning Reading mode, Folded Recall mode, focus view,
  bookmarks, difficult-word review, band/topic filtering, pagination, CSV
  import/export, speech, and local progress persistence are implemented in the
  inline JavaScript in `index.html`.
- Pagination is already used for library/search views, but the daily selection
  and all records are held in JavaScript memory. The final release must keep
  the rendered DOM bounded while making the local definition corpus available.
- Progress and bookmarks are stored under the `foldlex-notebook-v1` localStorage
  key. This key and its normalized word IDs must remain compatible.
- IndexedDB is currently used for definitions learned through the online API;
  it is not yet the packaged source of truth.

## Existing build utilities and provenance

- `source/100K/build.py` is a one-off generator from an earlier development
  path. It uses SCOWL/Hunspell, CMUdict, and TextBlob to create the 100K word
  list and adds only a small number of morphology notes.
- `tools/build_from_wordnet.py` is an earlier Open English WordNet utility. It
  can replace the bulk collection with WordNet-defined entries, but it does not
  preserve the canonical 100K list, does not merge Wiktionary/GCIDE, and does
  not emit provenance, stable IDs, quality reports, or tests.
- Existing license files cover SCOWL/Hunspell, CMUdict, and Open English
  WordNet attribution. The final data build will add source metadata and
  attribution for every imported lexical source.

## Data-quality risks found

- The preserved list includes inflections, technical terms, compounds, and
  proper-noun-like items. It is not guaranteed that every row is a valid
  general-English lexical item.
- Some current rows are only word forms generated from spelling resources; a
  suffix or prefix rule alone is not evidence for a definition.
- The CSV is UTF-8 with BOM and currently has no part-of-speech, source, or
  confidence columns. These will be added to the build artifacts while keeping
  the original word/band/topic fields and normalized IDs compatible.
- The final reports must distinguish verified dictionary definitions,
  morphology-derived definitions, model-generated definitions (if any), manual
  review, and genuinely unresolved rows. No unresolved row may receive a
  placeholder definition.

## Planned implementation boundary

1. Preserve the canonical words, bands, topics, and normalized IDs.
2. Build a reproducible local lexical merge from approved open sources,
   starting with Open English WordNet and adding compatible sources only when
   licensing and source data are available.
3. Emit a versioned local dataset and coverage/quality reports.
4. Make the app load the packaged dataset offline, keep user data compatible,
   and retain all existing learning actions.
5. Add automated integrity, coverage, provenance, and offline smoke tests.

