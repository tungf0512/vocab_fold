#!/usr/bin/env python3
"""Create a clean downloadable FoldLex ZIP without raw source archives."""
from __future__ import annotations

from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "FoldLex-offline-release.zip"
EXCLUDED_DIRS = {".cache", "__pycache__", ".git", "versions", "source", "previews"}
EXCLUDED_SUFFIXES = {".pyc", ".part", ".zip"}


def included(path: Path, output: Path) -> bool:
    if path == output or any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
        return False
    if path.name.startswith(".") and path.name != ".gitignore":
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def main() -> int:
    output = DEFAULT_OUTPUT
    if output.exists():
        output.unlink()
    files = sorted((path for path in ROOT.rglob("*") if included(path, output)), key=lambda p: p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            archive.write(path, relative)
    print(f"Packaged {len(files):,} files into {output} ({output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

