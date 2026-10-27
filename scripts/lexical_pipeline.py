#!/usr/bin/env python3
"""Shared, deterministic helpers for the FoldLex offline lexical build.

The module deliberately keeps source parsing separate from the browser build.
It never invents a definition from spelling alone: morphology is accepted only
when a licensed morphological resource links a surface form to a dictionary
lemma that already has a real definition.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
import csv
import gzip
import html
import json
from pathlib import Path
import re
import tarfile
from typing import Iterable, Iterator

try:
    from lxml import etree
except ImportError:  # pragma: no cover - reported by the CLI with a clear hint
    etree = None


WORD_RE = re.compile(r"^[a-z][a-z\u2019' .\-]{0,88}$", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(
    r"\b(?:definition not available|no definition|lookup required|online lookup|"
    r"definition unavailable|tbd|todo|placeholder|unknown meaning)\b",
    re.IGNORECASE,
)
TAG_RE = re.compile(r"<[^>]+>")
TEMPLATE_RE = re.compile(r"\{\{[^{}]*\}\}")
LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


@dataclass
class Candidate:
    definition: str
    senses: list[str]
    example: str
    part_of_speech: str
    source: str
    confidence: str
    generated: bool = False
    morphology_root: str = ""
    morphology_relation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_word(value: object) -> str:
    value = str(value or "").replace("_", " ").replace("’", "'")
    return " ".join(value.strip().casefold().split())


def clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = TEMPLATE_RE.sub("", text)
    text = LINK_RE.sub(lambda m: m.group(2) or m.group(1), text)
    text = TAG_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" ;\t\r\n")
    return text


def english_text(value: str) -> bool:
    """Conservative check used to reject malformed/non-English glosses."""
    text = clean_text(value)
    letters = sum(c.isalpha() for c in text)
    ascii_letters = sum(c.isascii() and c.isalpha() for c in text)
    words = re.findall(r"[A-Za-z]{2,}", text)
    return bool(text and len(text) >= 5 and len(words) >= 2 and ascii_letters >= max(4, letters * 0.55))


def valid_definition(word: str, definition: str) -> bool:
    definition = clean_text(definition)
    if not english_text(definition) or len(definition) > 1200:
        return False
    if PLACEHOLDER_RE.search(definition):
        return False
    normalized_definition = normalize_word(definition).strip(" .")
    if normalized_definition in {word, f"the meaning of {word}", f"a {word}"}:
        return False
    return True


def pos_name(value: str) -> str:
    return {
        "n": "noun",
        "v": "verb",
        "a": "adjective",
        "s": "adjective",
        "r": "adverb",
        "adj": "adjective",
        "adv": "adverb",
        "pron": "pronoun",
        "prep": "preposition",
        "conj": "conjunction",
        "det": "determiner",
        "intj": "interjection",
    }.get(str(value or "").casefold(), str(value or "").casefold() or "unknown")


def make_candidate(
    definitions: Iterable[str],
    *,
    example: str = "",
    part_of_speech: str = "",
    source: str,
    confidence: str = "high",
    generated: bool = False,
    morphology_root: str = "",
    morphology_relation: str = "",
) -> Candidate | None:
    senses: list[str] = []
    for raw in definitions:
        definition = clean_text(raw)
        if definition and definition not in senses and english_text(definition):
            senses.append(definition)
        if len(senses) >= 3:
            break
    if not senses:
        return None
    return Candidate(
        definition=senses[0],
        senses=senses,
        example=clean_text(example),
        part_of_speech=pos_name(part_of_speech),
        source=source,
        confidence=confidence,
        generated=generated,
        morphology_root=morphology_root,
        morphology_relation=morphology_relation,
    )


def load_vocabulary(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {"Word", "Band", "Topic"}
    if not rows or not expected.issubset(rows[0]):
        raise ValueError(f"{path} must contain {sorted(expected)} columns")
    result = []
    seen: set[str] = set()
    for position, row in enumerate(rows, start=1):
        word = normalize_word(row.get("Word"))
        if not word or word in seen:
            raise ValueError(f"duplicate or empty vocabulary word at CSV row {position + 1}: {row.get('Word')!r}")
        if not WORD_RE.fullmatch(word):
            raise ValueError(f"unsupported word characters at CSV row {position + 1}: {word!r}")
        seen.add(word)
        band = int(float(str(row.get("Band", "7")).strip() or 7))
        if band not in {4, 5, 6, 7, 8, 9}:
            raise ValueError(f"invalid band at CSV row {position + 1}: {band}")
        result.append(
            {
                "id": word,
                "word": row.get("Word", "").strip(),
                "normalized_word": word,
                "band": band,
                "topic": row.get("Topic", "").strip() or "General vocabulary",
                "legacy_definition": row.get("Explanation", "").strip(),
            }
        )
    return result


def load_legacy_curated(html_path: Path) -> dict[str, Candidate]:
    """Read the original 514 hand-written seed meanings from the HTML."""
    text = html_path.read_text(encoding="utf-8")
    match = re.search(r'<script id="seed-data" type="application/json">(.*?)</script>', text, re.S)
    if not match:
        return {}
    entries = json.loads(match.group(1))
    result: dict[str, Candidate] = {}
    for row in entries:
        if len(row) < 4 or not row[3]:
            continue
        word = normalize_word(row[2])
        candidate = make_candidate(
            [row[3]],
            source="foldlex-curated",
            confidence="high",
        )
        if candidate:
            result[word] = candidate
    return result


def parse_oewn(path: Path, targets: set[str]) -> tuple[dict[str, Candidate], dict[str, list[tuple[str, set[str]]]]]:
    if etree is None:
        raise RuntimeError("Open English WordNet parsing requires lxml; install it with `python -m pip install lxml`.")
    mappings: dict[str, list[str]] = defaultdict(list)
    pos_map: dict[str, set[str]] = defaultdict(set)
    synsets: dict[str, tuple[list[str], list[str]]] = {}
    with gzip.open(path, "rb") as stream:
        context = etree.iterparse(
            stream,
            events=("end",),
            tag=("{*}LexicalEntry", "{*}Synset", "LexicalEntry", "Synset"),
            load_dtd=False,
            no_network=True,
            resolve_entities=False,
        )
        for _, element in context:
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "LexicalEntry":
                lemma = next((child for child in element if child.tag.rsplit("}", 1)[-1] == "Lemma"), None)
                if lemma is not None:
                    word = normalize_word(lemma.get("writtenForm", ""))
                    if word in targets:
                        sense_ids = [
                            child.get("synset")
                            for child in element
                            if child.tag.rsplit("}", 1)[-1] == "Sense" and child.get("synset")
                        ]
                        mappings[word].extend(sense_ids)
                        pos_map[word].add(lemma.get("partOfSpeech", ""))
            else:
                definitions = [
                    clean_text("".join(child.itertext()))
                    for child in element
                    if child.tag.rsplit("}", 1)[-1] == "Definition"
                ]
                examples = [
                    clean_text("".join(child.itertext()))
                    for child in element
                    if child.tag.rsplit("}", 1)[-1] in {"Example", "ExampleSentence"}
                ]
                if definitions:
                    synsets[element.get("id", "")] = (definitions, examples)
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]
    result: dict[str, Candidate] = {}
    metadata: dict[str, list[tuple[str, set[str]]]] = {}
    for word, sense_ids in mappings.items():
        definitions: list[str] = []
        example = ""
        for sense_id in sense_ids:
            defs, examples = synsets.get(sense_id, ([], []))
            for definition in defs:
                if definition not in definitions and english_text(definition):
                    definitions.append(definition)
                if len(definitions) >= 3:
                    break
            if not example and examples:
                example = examples[0]
            if len(definitions) >= 3:
                break
        candidate = make_candidate(
            definitions,
            example=example,
            part_of_speech=sorted(pos_map.get(word, {""}))[0],
            source="open-english-wordnet-2025-plus",
            confidence="high",
        )
        if candidate:
            result[word] = candidate
            metadata[word] = [(word, pos_map[word])]
    return result, metadata


def parse_wiktionary(
    path: Path, targets: set[str]
) -> tuple[dict[str, Candidate], dict[str, list[tuple[str, list[str], str]]]]:
    """Read only target entries and target forms from the Kaikki JSONL dump."""
    direct: dict[str, list[tuple[list[str], list[str], str, list[str]]]] = defaultdict(list)
    forms: dict[str, list[tuple[str, list[str], str]]] = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("lang_code") not in {None, "en"} and item.get("lang") not in {None, "English"}:
                continue
            lemma = normalize_word(item.get("word", ""))
            if not lemma:
                continue
            pos = item.get("pos", "")
            senses = item.get("senses") or []
            definitions: list[str] = []
            examples: list[str] = []
            for sense in senses:
                for raw in sense.get("glosses", []) or sense.get("raw_glosses", []):
                    cleaned = clean_text(raw)
                    if cleaned and cleaned not in definitions and english_text(cleaned):
                        definitions.append(cleaned)
                for example in sense.get("examples", []) or []:
                    if isinstance(example, dict):
                        example = example.get("text", "")
                    cleaned = clean_text(example)
                    if cleaned and cleaned not in examples:
                        examples.append(cleaned)
                if len(definitions) >= 3:
                    break
            if lemma in targets and definitions:
                direct[lemma].append((definitions[:3], examples[:1], pos, [str(x) for x in item.get("tags", [])]))
            for form in item.get("forms", []) or []:
                form_word = normalize_word(form.get("form", "")) if isinstance(form, dict) else ""
                if form_word in targets and form_word != lemma:
                    tags = [str(tag).casefold() for tag in (form.get("tags", []) or [])] if isinstance(form, dict) else []
                    forms[form_word].append((lemma, tags, pos))
    result: dict[str, Candidate] = {}
    for word, candidates in direct.items():
        # Prefer a non-obsolete entry, then the one with the most useful senses.
        candidates.sort(key=lambda x: (any(tag in {"obsolete", "archaic", "dated"} for tag in x[3]), -len(x[0])))
        definitions, examples, pos, _ = candidates[0]
        candidate = make_candidate(
            definitions,
            example=examples[0] if examples else "",
            part_of_speech=pos,
            source="wiktionary-kaikki-english",
            confidence="high",
        )
        if candidate:
            result[word] = candidate
    return result, forms


def parse_gcide(path: Path, targets: set[str]) -> dict[str, Candidate]:
    """Read the ASCII CIDE.* files from GCIDE 0.53.

    GCIDE is an older dictionary, so it is intentionally a later fallback than
    Open English WordNet and Wiktionary. It still contributes useful verified
    entries for rare scientific and historical vocabulary.
    """
    if path.is_file() and path.suffix in {".xz", ".gz", ".bz2", ".zip", ".tar"}:
        raise ValueError("GCIDE must be an extracted directory; run download_sources.py first")
    files = sorted(path.glob("CIDE.*")) if path.is_dir() else []
    result: dict[str, Candidate] = {}
    for file_path in files:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        for block in re.findall(r"<p>(.*?)</p>", text, flags=re.IGNORECASE | re.DOTALL):
            entries = re.findall(r"<ent>(.*?)</ent>", block, flags=re.IGNORECASE | re.DOTALL)
            raw_defs = re.findall(r"<def>(.*?)</def>", block, flags=re.IGNORECASE | re.DOTALL)
            if not entries or not raw_defs:
                continue
            definitions = [clean_text(raw) for raw in raw_defs]
            pos_match = re.search(r"<pos>(.*?)</pos>", block, flags=re.IGNORECASE | re.DOTALL)
            part_of_speech = clean_text(pos_match.group(1)) if pos_match else ""
            candidate = make_candidate(
                definitions,
                part_of_speech=part_of_speech,
                source="gcide-0.53",
                confidence="medium",
            )
            if not candidate:
                continue
            for raw_entry in entries:
                word = normalize_word(clean_text(raw_entry))
                if word in targets and word not in result:
                    result[word] = candidate
    return result


def load_hunspell_forms(
    aff_path: Path | None,
    dic_path: Path | None,
    targets: set[str],
) -> dict[str, list[tuple[str, str]]]:
    """Generate surface forms using documented Hunspell affix rules."""
    if not aff_path or not dic_path or not aff_path.exists() or not dic_path.exists():
        return {}
    lines = aff_path.read_text(encoding="utf-8", errors="replace").splitlines()
    patterns: dict[tuple[str, str], list[tuple[str, str, re.Pattern[str]]]] = {}
    i = 0
    while i < len(lines):
        fields = lines[i].split()
        if len(fields) >= 4 and fields[0] in {"SFX", "PFX"}:
            kind, flag, _cross, count_text = fields[:4]
            count = int(count_text)
            rules = []
            for raw in lines[i + 1 : i + count + 1]:
                rule = raw.split()
                if len(rule) < 5 or rule[0] != kind or rule[1] != flag:
                    continue
                try:
                    pattern = re.compile((rule[4] + "$" if kind == "SFX" else "^" + rule[4]))
                except re.error:
                    continue
                rules.append((rule[2], rule[3].split("/")[0], pattern))
            patterns[(kind, flag)] = rules
            i += count + 1
        else:
            i += 1
    forms: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for raw in dic_path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        if not raw.strip():
            continue
        first = raw.split()[0].split("/", 1)
        root = normalize_word(first[0])
        if not re.fullmatch(r"[a-z]{2,32}", root):
            continue
        flags = first[1] if len(first) > 1 else ""
        for flag in set(flags):
            for kind in ("SFX", "PFX"):
                for strip, add, pattern in patterns.get((kind, flag), []):
                    if not pattern.search(root):
                        continue
                    stripped = "" if strip == "0" else strip
                    added = "" if add == "0" else add
                    if kind == "SFX":
                        word = (root[: -len(stripped)] if stripped else root) + added
                    else:
                        word = added + (root[len(stripped) :] if stripped else root)
                    if word in targets and word != root:
                        forms[word].append((root, flag))
    return dict(forms)


def morphology_relation(word: str, root: str, part_of_speech: str, tags: Iterable[str] = ()) -> str:
    tag_text = " ".join(str(x).casefold() for x in tags)
    if "plural" in tag_text or (part_of_speech == "noun" and word.endswith(("s", "es", "ies"))):
        return "plural"
    if "comparative" in tag_text or (part_of_speech == "adjective" and word.endswith("er") and len(word) > len(root)):
        return "comparative"
    if "superlative" in tag_text or (part_of_speech == "adjective" and word.endswith("est") and len(word) > len(root)):
        return "superlative"
    if "present participle" in tag_text or "gerund" in tag_text or (part_of_speech == "verb" and word.endswith("ing")):
        return "present participle or gerund"
    if "past" in tag_text or "participle" in tag_text or (part_of_speech == "verb" and word.endswith("ed")):
        return "past tense or past participle"
    if "third-person" in tag_text or (part_of_speech == "verb" and word.endswith("s")):
        return "third-person singular"
    return ""


def morphology_candidate(word: str, root: str, base: Candidate, tags: Iterable[str] = ()) -> Candidate | None:
    relation = morphology_relation(word, root, base.part_of_speech, tags)
    if not relation:
        return None
    article = {
        "plural": f'The plural form of “{root}”.',
        "comparative": f'The comparative form of “{root}”.',
        "superlative": f'The superlative form of “{root}”.',
        "present participle or gerund": f'The present participle or gerund of “{root}”.',
        "past tense or past participle": f'The past tense or past participle of “{root}”.',
        "third-person singular": f'The third-person singular form of “{root}”.',
    }[relation]
    return Candidate(
        definition=article + (f" {base.definition}" if base.definition else ""),
        senses=[article + (f" {sense}" if sense else "") for sense in base.senses[:3]],
        example=base.example,
        part_of_speech=base.part_of_speech,
        source=f"{base.source}+morphology",
        confidence="medium",
        generated=True,
        morphology_root=root,
        morphology_relation=relation,
    )


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

