#!/usr/bin/env python3
"""Build the complete local FoldLex data package and standalone HTML release."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lexical_pipeline import (  # noqa: E402
    Candidate,
    load_hunspell_forms,
    load_legacy_curated,
    load_vocabulary,
    make_candidate,
    morphology_candidate,
    normalize_word,
    parse_oewn,
    parse_gcide,
    parse_wiktionary,
    valid_definition,
    write_json,
)


DEFAULT_WORDNET = ROOT / ".cache" / "foldlex-sources" / "english-wordnet-2025-plus.xml.gz"
DEFAULT_WIKTIONARY = ROOT / ".cache" / "foldlex-sources" / "kaikki-English.jsonl.gz"
DEFAULT_GCIDE = ROOT / ".cache" / "foldlex-sources" / "gcide-0.53"


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocabulary", type=Path, default=ROOT / "data/FoldLex-100000-Vocabulary.csv")
    parser.add_argument("--website", type=Path, default=ROOT / "index.html")
    parser.add_argument("--wordnet", type=Path, default=DEFAULT_WORDNET)
    parser.add_argument("--wiktionary", type=Path, default=DEFAULT_WIKTIONARY)
    parser.add_argument("--gcide", type=Path, default=DEFAULT_GCIDE, help="extracted GCIDE 0.53 directory; optional")
    parser.add_argument("--hunspell-aff", type=Path, default=Path("/usr/share/hunspell/en_US.aff"))
    parser.add_argument("--hunspell-dic", type=Path, default=Path("/usr/share/hunspell/en_US.dic"))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--allow-unresolved", action="store_true", help="write a release even when some rows lack evidence")
    parser.add_argument("--no-wiktionary", action="store_true", help="build from WordNet and morphology only")
    parser.add_argument("--no-gcide", action="store_true", help="omit the optional GCIDE fallback")
    return parser


def candidate_is_usable(candidate: Candidate | None) -> bool:
    return bool(candidate and valid_definition("", candidate.definition))


def unresolved_reason(word: str) -> str:
    if re.fullmatch(r"[ivxlcdm]+", word):
        return "Roman numeral or code-like token; no English lexical sense verified"
    if len(word) <= 4:
        return "short or abbreviation-like token; manual lexical review required"
    if re.search(r"(.)\1\1", word):
        return "possible typo, OCR artifact, or nonstandard token"
    if word.endswith(("s", "ed", "ing", "ly", "ness", "tion", "ment", "able", "al", "ic")):
        return "possible inflected or derived form not linked to a verified lemma"
    return "not found in approved lexical sources; manual lexical review required"


def build_records(args: argparse.Namespace) -> tuple[list[dict], dict]:
    rows = load_vocabulary(args.vocabulary)
    if len(rows) != 100_000:
        raise ValueError(f"Expected exactly 100,000 canonical rows, found {len(rows):,}")
    targets = {row["normalized_word"] for row in rows}
    legacy_curated = load_legacy_curated(args.website)

    if not args.wordnet.exists():
        raise FileNotFoundError(f"Missing Open English WordNet archive: {args.wordnet}")
    print("Parsing Open English WordNet…", flush=True)
    wordnet, _wordnet_meta = parse_oewn(args.wordnet, targets)
    wiktionary: dict[str, Candidate] = {}
    wiktionary_forms: dict[str, list[tuple[str, list[str], str]]] = {}
    if not args.no_wiktionary:
        if not args.wiktionary.exists():
            raise FileNotFoundError(f"Missing Kaikki/Wiktionary archive: {args.wiktionary}")
        print("Parsing Kaikki English Wiktionary extraction…", flush=True)
        wiktionary, wiktionary_forms = parse_wiktionary(args.wiktionary, targets)
    gcide: dict[str, Candidate] = {}
    if not args.no_gcide and args.gcide.exists():
        print("Parsing GCIDE 0.53 fallback…", flush=True)
        gcide = parse_gcide(args.gcide, targets)
    hunspell_forms = load_hunspell_forms(args.hunspell_aff, args.hunspell_dic, targets)

    # Existing hand-written explanations remain stable and take precedence over
    # dictionary wording for the original 514 curated entries.
    direct: dict[str, Candidate] = {}
    for word in targets:
        if word in legacy_curated:
            direct[word] = legacy_curated[word]
        elif word in wordnet:
            direct[word] = wordnet[word]
        elif word in wiktionary:
            direct[word] = wiktionary[word]
        elif word in gcide:
            direct[word] = gcide[word]

    # Only use the 118 old morphology notes as a last resort, never as evidence
    # for a new word. They are retained for compatibility and marked generated.
    legacy_rows = {row["normalized_word"]: row["legacy_definition"] for row in rows if row["legacy_definition"]}
    for word, definition in legacy_rows.items():
        if word in direct:
            continue
        candidate = make_candidate(
            [definition],
            source="foldlex-legacy-morphology",
            confidence="low",
            generated=True,
        )
        if candidate:
            direct[word] = candidate

    # Root candidates are only real dictionary entries. Generated forms are not
    # allowed to become roots for another generated form (avoids chains such as
    # an already-derived word -> another invented derivative).
    root_candidates = {word: candidate for word, candidate in direct.items() if not candidate.generated or candidate.source == "foldlex-curated"}
    generated: dict[str, Candidate] = {}

    for word in sorted(targets - set(direct)):
        roots = sorted({root for root, _tags, _pos in wiktionary_forms.get(word, []) if root in root_candidates})
        if len(roots) == 1:
            root = roots[0]
            forms_for_root = [entry for entry in wiktionary_forms[word] if entry[0] == root]
            tags = forms_for_root[0][1] if forms_for_root else []
            candidate = morphology_candidate(word, root, root_candidates[root], tags)
            if candidate:
                generated[word] = candidate
                continue
        roots = sorted({root for root, _flag in hunspell_forms.get(word, []) if root in root_candidates})
        if len(roots) == 1:
            root = roots[0]
            candidate = morphology_candidate(word, root, root_candidates[root])
            if candidate:
                generated[word] = candidate

    unresolved = []
    output: list[dict] = []
    for row in rows:
        word = row["normalized_word"]
        candidate = direct.get(word) or generated.get(word)
        if not candidate:
            unresolved.append(row)
        output.append(
            {
                "id": row["id"],
                "word": row["word"],
                "band": row["band"],
                "topic": row["topic"],
                "part_of_speech": candidate.part_of_speech if candidate else "unknown",
                "definition": candidate.definition if candidate else "",
                "senses": candidate.senses if candidate else [],
                "example": candidate.example if candidate else "",
                "source": candidate.source if candidate else "unresolved",
                "confidence": candidate.confidence if candidate else "none",
                "generated": bool(candidate.generated) if candidate else False,
                "verified": bool(candidate and not candidate.generated),
                "morphology_root": candidate.morphology_root if candidate else "",
                "morphology_relation": candidate.morphology_relation if candidate else "",
                "unresolved_reason": "" if candidate else unresolved_reason(word),
            }
        )

    source_counts = Counter(item["source"] for item in output)
    confidence_counts = Counter(item["confidence"] for item in output)
    generated_count = sum(item["generated"] for item in output)
    verified_count = sum(item["verified"] for item in output)
    metrics = {
        "total_vocabulary_entries": len(output),
        "valid_lexical_entries": len(output) - len(unresolved),
        "entries_with_definition": sum(bool(item["definition"]) for item in output),
        "verified_definition_count": verified_count,
        "model_generated_definition_count": 0,
        "morphology_generated_definition_count": generated_count,
        "manual_review_count": sum(item["confidence"] == "low" or not item["definition"] for item in output),
        "unresolved_count": len(unresolved),
        "overall_definition_coverage_percent": round(100 * sum(bool(item["definition"]) for item in output) / len(output), 4),
        "verified_definition_coverage_percent": round(100 * verified_count / len(output), 4),
        "source_counts": dict(source_counts),
        "confidence_counts": dict(confidence_counts),
        "unresolved_reason_counts": dict(Counter(row["unresolved_reason"] for row in output if row["unresolved_reason"])),
        "unresolved_words": [row["word"] for row in unresolved],
        "source_archives": {
            "open_english_wordnet": args.wordnet.name,
            "wiktionary_kaikki": None if args.no_wiktionary else args.wiktionary.name,
            "gcide": None if args.no_gcide else args.gcide.name,
            "hunspell_aff": args.hunspell_aff.name,
            "hunspell_dic": args.hunspell_dic.name,
        },
    }
    if unresolved and not args.allow_unresolved:
        raise RuntimeError(
            f"{len(unresolved):,} canonical entries have no verified lexical evidence. "
            "Use --allow-unresolved to emit an honest partial package and inspect reports/unresolved-words.csv."
        )
    return output, metrics


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def replace_json_script(document: str, script_id: str, value: object) -> str:
    pattern = re.compile(rf'(<script id="{re.escape(script_id)}" type="application/json">).*?(</script>)', re.S)
    replacement = lambda match: match.group(1) + compact_json(value) + match.group(2)
    updated, count = pattern.subn(replacement, document, count=1)
    if count != 1:
        raise ValueError(f"Could not find {script_id} in {script_id} template")
    return updated


def patch_runtime(document: str, metrics: dict) -> str:
    """Remove online lookup and keep the current FoldLex UI/progress contract."""
    # The data blocks carry extra fields after the first four fields. Existing
    # progress IDs remain the normalized word, exactly as in the old app.
    document = document.replace(
        "const starter=JSON.parse($('#seed-data').textContent).map(([b,t,w,d])=>({band:Number(b),topic:t,word:w,definition:d,custom:false}));",
        "const starter=JSON.parse($('#seed-data').textContent).map(x=>({band:Number(x[0]),topic:x[1],word:x[2],definition:x[3]||'',partOfSpeech:x[4]||'',senses:Array.isArray(x[5])?x[5]:[],source:x[6]||'',confidence:x[7]||'',custom:false,online:false}));",
    )
    document = document.replace(
        "const expansion=JSON.parse(document.getElementById('bulk-data').textContent).map(x=>({band:x[0],topic:x[1],word:x[2],definition:x[3]||'',online:!x[3]}));",
        "const expansion=JSON.parse(document.getElementById('bulk-data').textContent).map(x=>({band:x[0],topic:x[1],word:x[2],definition:x[3]||'',partOfSpeech:x[4]||'',senses:Array.isArray(x[5])?x[5]:[],source:x[6]||'',confidence:x[7]||'',online:false}));",
    )
    document = document.replace(",offlineOnly:true", "")
    document = document.replace(";if(state.offlineOnly)xs=xs.filter(r=>Boolean(r.definition))", "")
    document = document.replace("$('#offlineFilter').classList.toggle('active',state.offlineOnly);$('#offlineFilter').setAttribute('aria-pressed',String(state.offlineOnly));", "")
    document = document.replace(
        "$('#offlineFilter').addEventListener('click',()=>{state.offlineOnly=!state.offlineOnly;state.deckKey=null;state.page=0;state.revealed.clear();render();notify(state.offlineOnly?'Only bundled English explanations are shown.':'All 100,000 words are now available.');});",
        "",
    )
    document = re.sub(r"const lookupStatus=.*?function render\(\)", "function render()", document, count=1, flags=re.S)
    document = re.sub(r"function explain\(r\)\{.*?\}\nfunction paperRows", """function explain(r){
  if(!r.definition)return '<span class=\"dictionary-msg\">No verified English definition is packaged for this entry. See the unresolved report.</span>';
  const extra=(r.senses||[]).slice(1);
  return encode(r.definition)+(extra.length?'<details class=\"sense-details\"><summary>More senses ('+extra.length+')</summary><ul>'+extra.map(x=>'<li>'+encode(x)+'</li>').join('')+'</ul></details>':'');
}
function paperRows""", document, count=1, flags=re.S)
    document = document.replace("requestDefinitions(items.filter(r=>state.mode==='morning'||state.revealed.has(r.id)));", "")
    document = re.sub(
        r"async function exportCSV\(\)\{.*?\}\nfunction exportJSON",
        lambda _match: "function exportCSV(){const rows=[['Word','Explanation','Band','Topic'],...records.map(r=>[r.word,r.definition||'',r.band,r.topic])];download('foldlex-vocabulary.csv','text/csv;charset=utf-8','\\uFEFF'+rows.map(row=>row.map(csvField).join(',')).join('\\r\\n'));notify('Vocabulary exported as CSV.')}\nfunction exportJSON",
        document,
        count=1,
        flags=re.S,
    )
    lookup_start = document.find("$('#lookupBtn').addEventListener")
    nav_start = document.find("\n$$('.nav-btn')", lookup_start)
    if lookup_start >= 0 and nav_start >= 0:
        document = document[:lookup_start] + document[nav_start:]
    document = document.replace("$('#dateText').textContent", "$('#dateText').textContent")
    document = document.replace("allData();updateTopics();render();dbGetAll().then(m=>{let n=0;for(const [w,d] of m){const r=byId.get(w);if(r&&!r.definition){r.definition=d;n++;}}if(n){statsDirty=true;state.deckKey=null;render();}});", "allData();updateTopics();render();")
    document = document.replace(
        "const labels={today:[\"Your daily vocabulary sheet\",\"Your daily paper-style review. Choose Offline meanings to study without Internet.\"],library:[\"Your vocabulary library\",\"Browse 100,000 entries across estimated bands. For offline study, use the Offline meanings filter.\"],",
        "const labels={today:[\"Your daily vocabulary sheet\",\"Your daily paper-style review with locally bundled English explanations.\"],library:[\"Your vocabulary library\",\"Browse 100,000 entries across estimated learning bands.\"],",
    )
    document = document.replace(
        "let n=records.reduce((t,r)=>t+Boolean(r.definition),0);cc.textContent=records.length.toLocaleString('en-US')+' vocabulary entries stored offline · '+n.toLocaleString('en-US')+' verified English explanations available offline · '+(records.length-n).toLocaleString('en-US')+' definitions missing. Toggle Offline meanings to study complete cards. The ZIP includes a dictionary-building tool.';",
        "let n=records.reduce((t,r)=>t+Boolean(r.definition),0);cc.textContent=records.length.toLocaleString('en-US')+' vocabulary entries stored offline · '+n.toLocaleString('en-US')+' local explanations available · '+(records.length-n).toLocaleString('en-US')+' entries listed in the build report as unresolved.';",
    )
    # Debounce search without changing the existing input, pagination, or mode API.
    document = document.replace(
        "$('#searchInput').addEventListener('input',e=>{state.search=e.target.value;state.page=0;state.focusIndex=0;render()});",
        "let searchTimer;$('#searchInput').addEventListener('input',e=>{clearTimeout(searchTimer);const value=e.target.value;searchTimer=setTimeout(()=>{state.search=value;state.page=0;state.focusIndex=0;render()},150)});",
    )
    document = document.replace("const offline= newWords.filter", "const offline= newWords.filter")
    # HTML-facing text is patched separately below; this keeps the app code
    # free of claims that meanings are retrieved online.
    return document


def patch_html(template: Path, records: list[dict], metrics: dict) -> str:
    document = template.read_text(encoding="utf-8")
    seed_words = [normalize_word(row[2]) for row in json.loads(re.search(r'<script id="seed-data" type="application/json">(.*?)</script>', document, re.S).group(1))]
    by_word = {row["id"]: row for row in records}
    seed_set = set(seed_words)

    def app_row(row: dict) -> list:
        return [
            row["band"],
            row["topic"],
            row["word"],
            row["definition"],
            row["part_of_speech"],
            row["senses"],
            row["source"],
            row["confidence"],
        ]

    seed_payload = [app_row(by_word[word]) for word in seed_words if word in by_word]
    bulk_payload = [app_row(row) for row in records if row["id"] not in seed_set]
    document = replace_json_script(document, "seed-data", seed_payload)
    document = replace_json_script(document, "bulk-data", bulk_payload)

    definitions = metrics["entries_with_definition"]
    unresolved = metrics["unresolved_count"]
    coverage_text = (
        f"{metrics['total_vocabulary_entries']:,} vocabulary entries stored offline · "
        f"{definitions:,} local English explanations bundled · "
        f"{unresolved:,} entries listed transparently in the unresolved report."
    )
    document = re.sub(
        r'(<div id="coverageNotice"[^>]*>).*?(</div>)',
        lambda m: m.group(1) + coverage_text + m.group(2),
        document,
        count=1,
        flags=re.S,
    )
    document = re.sub(
        r'<div class="online-note">.*?</div>',
        '<div class="online-note"><b>Offline dictionary</b> · Every packaged explanation is stored in this HTML and in the local data files. Band labels are estimated learning difficulty, not official IELTS word ratings.</div>',
        document,
        count=1,
        flags=re.S,
    )
    document = re.sub(
        r'<button aria-label="Only words with offline English definitions".*?</button>',
        '<span class="offline-badge" title="Definitions are bundled locally">✓ Bundled offline</span>',
        document,
        count=1,
        flags=re.S,
    )
    document = re.sub(
        r'<button class="btn-secondary" id="lookupBtn".*?</button>',
        '<span class="btn-secondary" style="display:inline-block">Write manually</span>',
        document,
        count=1,
        flags=re.S,
    )
    document = document.replace(
        "Dictionary lookup needs an internet connection. Your own entries work offline.",
        "Built-in explanations work offline. Add your own English explanation for personal entries.",
    )
    document = document.replace(
        "Built-in words will not be overwritten by a CSV import. Exported meanings only include available or previously cached explanations; unknown definitions are left blank.",
        "A CSV import can update existing normalized words or add personal entries. Built-in definitions remain in the packaged release.",
    )
    document = document.replace(
        "514 starter explanations are included for offline use. The full set of 100,000 English headwords and inflected forms is stored locally. The curated definitions are bundled; missing definitions are not invented and may be imported in bulk with CSV or built from open dictionaries. An optional WordNet offline build is available in the ZIP. Vocabulary may have additional meanings, grammar patterns and collocations not shown here. Your own notes and CSV imports help you tailor it.",
        f"{definitions:,} local English explanations are included in this release. Each record has source and confidence metadata in data/definitions.json; generated morphology notes are labeled separately and unresolved rows are reported rather than filled with placeholders. Vocabulary may have additional meanings, grammar patterns and collocations not shown in the primary column. Your own notes and CSV imports help you tailor it.",
    )
    document = document.replace(
        "Offline-first for built-in notes; internet is required for new dictionary definitions unless you generate the extended offline edition. No login, no tracker, no cloud sync. Browser speech requires supported system voices. Optional dictionary lookup uses dictionaryapi.dev when online.",
        "The built-in dictionary works without Internet access. No login, no tracker, no cloud sync. Browser speech requires supported system voices. The build pipeline and source licenses are documented in the ZIP.",
    )
    style_add = '.offline-badge{color:#258269;background:#f1fbf5;border:1px solid #d9f0e2;border-radius:7px;padding:6px 9px;font-size:10px;font-weight:800;white-space:nowrap}.sense-details{margin-top:8px;color:#747d91;font-size:11px}.sense-details summary{cursor:pointer;color:#7465bd;font-weight:750}.sense-details ul{margin:6px 0 0 18px;padding:0}'
    document = document.replace(style_add, '')
    document = document.replace('.hide{display:none!important}', style_add + '.hide{display:none!important}')
    return patch_runtime(document, metrics)


def write_outputs(args: argparse.Namespace, records: list[dict], metrics: dict) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "definitions.json", records)
    write_json(args.output_dir / "definitions-index.json", {row["id"]: i for i, row in enumerate(records)})
    metadata = {
        "schema_version": 1,
        "dataset": "FoldLex IELTS Vocabulary Notebook",
        "canonical_entry_count": len(records),
        "id_strategy": "casefolded normalized Word; compatible with foldlex-notebook-v1 progress IDs",
        "definition_fields": ["definition", "senses", "example", "part_of_speech", "source", "confidence", "generated", "verified"],
        "license_summary": {
            "open_english_wordnet": "CC BY 4.0",
            "wiktionary_kaikki": "Wiktionary-derived content, CC BY-SA 4.0; share-alike attribution retained",
            "foldlex_curated": "Original FoldLex text; see project license",
            "scowl_hunspell_morphology": "See LICENSES/SCOWL-HUNSPELL.txt",
        },
        "metrics": metrics,
        "built_on": str(date.today()),
    }
    manifest_path = args.wordnet.parent / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for spec in manifest.get("sources", {}).values():
                if isinstance(spec, dict):
                    if spec.get("path"):
                        spec["path"] = Path(spec["path"]).name
                    if spec.get("extracted_path"):
                        spec["extracted_path"] = Path(spec["extracted_path"]).name
            metadata["source_manifest"] = manifest
        except json.JSONDecodeError:
            metadata["source_manifest"] = {"warning": "source manifest was not valid JSON"}
    write_json(args.output_dir / "metadata.json", metadata)
    with (args.output_dir / "vocabulary-100k-complete.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["id", "Word", "Band", "Topic", "Part of speech", "Explanation", "Additional senses", "Example", "Source", "Confidence", "Generated", "Verified"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    "id": row["id"],
                    "Word": row["word"],
                    "Band": row["band"],
                    "Topic": row["topic"],
                    "Part of speech": row["part_of_speech"],
                    "Explanation": row["definition"],
                    "Additional senses": " | ".join(row["senses"][1:]),
                    "Example": row["example"],
                    "Source": row["source"],
                    "Confidence": row["confidence"],
                    "Generated": str(row["generated"]).lower(),
                    "Verified": str(row["verified"]).lower(),
                }
            )
    unresolved = [row["word"] for row in records if not row["definition"]]
    with (args.reports_dir / "unresolved-words.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["word", "id", "band", "topic", "reason"])
        for row in records:
            if not row["definition"]:
                writer.writerow([row["word"], row["id"], row["band"], row["topic"], row["unresolved_reason"]])
    write_json(args.reports_dir / "coverage.json", metrics)

    original = args.website.read_text(encoding="utf-8")
    release = patch_html(args.website, records, metrics)
    args.website.with_name("index.html").write_text(release, encoding="utf-8")
    # `index.html` is the requested release entry point. A separate snapshot is
    # useful when re-running the builder against a template in development.
    (args.reports_dir / "build-summary.txt").write_text(
        f"Built {len(records):,} records; {metrics['entries_with_definition']:,} definitions; {metrics['unresolved_count']:,} unresolved.\n",
        encoding="utf-8",
    )
    print(json.dumps({k: v for k, v in metrics.items() if k not in {"unresolved_words", "source_archives"}}, indent=2))
    if original == release:
        print("warning: HTML content did not change", file=sys.stderr)


def main() -> int:
    args = argument_parser().parse_args()
    print(f"Loading canonical vocabulary: {args.vocabulary}", flush=True)
    records, metrics = build_records(args)
    write_outputs(args, records, metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

