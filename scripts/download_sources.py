#!/usr/bin/env python3
"""Download the open lexical inputs used by the FoldLex build.

Archives are kept in `.cache/foldlex-sources` by default and are intentionally
not copied into the release ZIP. Partial files are retained so an interrupted
download can be resumed with the next invocation when the server supports HTTP
Range requests.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "open_english_wordnet": {
        "filename": "english-wordnet-2025-plus.xml.gz",
        "url": "https://en-word.net/static/english-wordnet-2025-plus.xml.gz",
        "license": "CC BY 4.0",
        "attribution": "Open English WordNet Community, based on Princeton WordNet",
    },
    "wiktionary_kaikki": {
        "filename": "kaikki-English.jsonl.gz",
        "url": "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl.gz",
        "license": "Wiktionary-derived content, CC BY-SA 4.0",
        "attribution": "Wiktionary contributors; machine-readable extraction by Kaikki.org",
    },
    "gcide": {
        "filename": "gcide-0.53.tar.xz",
        "url": "https://ftp.gnu.org/gnu/gcide/gcide-0.53.tar.xz",
        "license": "GNU General Public License v3 or later",
        "attribution": "GNU Collaborative International Dictionary of English (GCIDE)",
    },
}


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    existing = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "FoldLex offline dataset builder/1.0"}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status = getattr(response, "status", 200)
            mode = "ab" if existing and status == 206 else "wb"
            if mode == "wb":
                existing = 0
            with partial.open(mode) as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
    except Exception:
        print(f"Download interrupted; retained {partial} for a future retry.")
        raise
    partial.replace(destination)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".cache/foldlex-sources")
    parser.add_argument("--wordnet-only", action="store_true")
    parser.add_argument("--skip-wiktionary", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    selected = ["open_english_wordnet"]
    if not args.wordnet_only:
        selected.append("gcide")
    if not args.wordnet_only and not args.skip_wiktionary:
        selected.append("wiktionary_kaikki")
    manifest = {"retrieved_on": str(date.today()), "sources": {}}
    for key in selected:
        spec = SOURCES[key]
        destination = args.output_dir / spec["filename"]
        if destination.exists():
            print(f"Using existing {destination}")
        else:
            print(f"Downloading {key} from {spec['url']}")
            download(spec["url"], destination)
        manifest["sources"][key] = {**spec, "path": str(destination), "sha256": sha256(destination), "bytes": destination.stat().st_size}
        print(f"  {destination.stat().st_size:,} bytes  sha256={manifest['sources'][key]['sha256']}")
        if key == "gcide":
            extracted = args.output_dir / "gcide-0.53"
            if not extracted.exists():
                print(f"Extracting GCIDE to {extracted}")
                with tarfile.open(destination, "r:xz") as archive:
                    archive.extractall(args.output_dir)
            manifest["sources"][key]["extracted_path"] = str(extracted)
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

