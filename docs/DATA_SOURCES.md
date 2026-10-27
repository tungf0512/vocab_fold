# FoldLex data sources and licensing

The packaged application contains local definition data. The browser does not
call an online dictionary service.

## Sources used by the build

1. **Open English WordNet 2025+** — primary direct-definition source. The
   official WN-LMF XML archive is downloaded from
   <https://en-word.net/static/english-wordnet-2025-plus.xml.gz>. It is
   distributed under CC BY 4.0. Keep the attribution in
   `LICENSES/WORDNET-ATTRIBUTION.txt` when redistributing a build.
2. **English Wiktionary via Kaikki.org** — gap-filling direct definitions and
   inflection metadata. The machine-readable extraction is
   <https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl.gz>.
   Wiktionary-derived text is CC BY-SA 4.0; the release retains source and
   share-alike attribution in `data/metadata.json` and this document.
3. **FoldLex curated text** — the original 514 learner-friendly explanations
   already distributed with the project. These remain stable where present.
4. **GCIDE 0.53** — a later fallback for rare and technical vocabulary. The
   official GNU archive is <https://ftp.gnu.org/gnu/gcide/gcide-0.53.tar.xz> and
   is GPLv3-or-later; see `LICENSES/GCIDE-ATTRIBUTION.txt`.
5. **SCOWL/Hunspell morphology** — only used to link a surface inflection to a
   root that already has a real lexical definition. It is never used by itself
   to invent a meaning. See `LICENSES/SCOWL-HUNSPELL.txt`.

## Provenance fields

Each record in `data/definitions.json` contains `source`, `confidence`,
`generated`, `verified`, `part_of_speech`, `senses`, and (when applicable)
`morphology_root`/`morphology_relation`. `reports/coverage.md` summarizes these
fields and `reports/quality-audit.md` provides a deterministic manual-review
sample.

The build does not copy raw dictionary dumps into the release ZIP. Re-run
`scripts/download_sources.py` to recreate the local cache, then rebuild.

