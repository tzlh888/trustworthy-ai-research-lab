#!/usr/bin/env python3
"""Build and verify a deterministic, public-safe V2 release candidate ZIP."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath


FIXED_TIMESTAMP = (2026, 10, 14, 0, 0, 0)
EXCLUDED_PARTS = {
    ".git", ".venv", "venv", ".cache", ".pytest_cache", "__pycache__",
    "tmp", "outputs", "data/raw", "audit",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".swp", ".tmp"}
EXCLUDED_NAMES = {".DS_Store", "FINAL_V2_HANDOFF.md", "OWNER_VERIFICATION_WORKSHEET.md"}
REQUIRED = {
    "README.md",
    "LICENSE",
    "CITATION.cff",
    "configs/research_upgrade_v2_protocol.json",
    "configs/research_upgrade_v2_correction_2026-10-14.json",
    "docs/PERSONAL_RESEARCH_CONTRIBUTION.md",
    "paper/Trustworthy_AI_Research_Lab_V2_Final.md",
    "paper/Trustworthy_AI_Research_Lab_V2_Final.pdf",
    "paper/Trustworthy_AI_Research_Lab_V2_One_Page.pdf",
    "paper/ARCHIVAL_NOTICE_2026-10-14.md",
    "portfolio/RESEARCH_CONTRIBUTION_PARAGRAPH.md",
    "reports/research_upgrade_v2/FINAL_CORRECTION_AUDIT.md",
    "reports/research_upgrade_v2/FINAL_REPRODUCIBILITY_VERIFICATION.md",
    "scripts/run_upgrade_v2_inference.py",
    "scripts/analyze_research_upgrade_v2.py",
    "scripts/build_v2_final_pdfs.py",
    "scripts/build_v2_release_candidate.py",
    "tests/test_research_upgrade_v2.py",
}
TEXT_SUFFIXES = {".md", ".py", ".toml", ".txt", ".json", ".yaml", ".yml", ".cff", ".csv"}
SENSITIVE_PATTERNS = {
    "absolute macOS user path": re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    "OpenAI-like secret": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "GitHub-like token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "assigned secret": re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_candidates(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return sorted(path for path in result.stdout.decode().split("\0") if path)


def _allowed(relative: str) -> bool:
    path = PurePosixPath(relative)
    parts = path.parts
    if not parts or path.is_absolute() or ".." in parts:
        return False
    if relative == "data/raw" or relative.startswith("data/raw/"):
        return False
    if any(part in EXCLUDED_PARTS for part in parts):
        return False
    if path.name in EXCLUDED_NAMES or path.suffix.casefold() in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith(".#") or path.name.endswith("~"):
        return False
    return True


def collect(root: Path) -> list[str]:
    files = [relative for relative in _git_candidates(root) if _allowed(relative)]
    missing = sorted(REQUIRED - set(files))
    if missing:
        raise RuntimeError(f"Required release files missing: {missing}")
    return files


def scan_source(root: Path, files: list[str]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for relative in files:
        path = root / relative
        if not path.is_file():
            findings.append({"path": relative, "finding": "not a regular file"})
            continue
        if path.suffix.casefold() not in TEXT_SUFFIXES and path.name not in {".gitignore", ".env.example"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(text):
                findings.append({"path": relative, "finding": name})
    return findings


def build(root: Path, output: Path) -> dict[str, object]:
    files = collect(root)
    findings = scan_source(root, files)
    if findings:
        raise RuntimeError(f"Source safety scan failed: {findings}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in files:
            info = zipfile.ZipInfo(relative, FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, (root / relative).read_bytes())
    with zipfile.ZipFile(output) as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise RuntimeError(f"ZIP integrity failure at {corrupt}")
        names = archive.namelist()
        if names != files:
            raise RuntimeError("ZIP entry list differs from the sorted source file list")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or not _allowed(name):
                raise RuntimeError(f"Unsafe or excluded ZIP entry: {name}")
    manifest: dict[str, object] = {
        "schema_version": 1,
        "status": "PASS",
        "candidate_not_published": True,
        "file_count": len(files),
        "zip_bytes": output.stat().st_size,
        "zip_sha256": sha256(output),
        "zip_integrity": "PASS",
        "path_safety": "PASS",
        "source_sensitive_scan": {"status": "PASS", "findings": []},
        "excluded_local_handoff": "FINAL_V2_HANDOFF.md",
        "files": [
            {"path": relative, "bytes": (root / relative).stat().st_size, "sha256": sha256(root / relative)}
            for relative in files
        ],
    }
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.root.resolve(), args.output.resolve())
    print(json.dumps({key: result[key] for key in ("status", "file_count", "zip_bytes", "zip_sha256")}, indent=2))


if __name__ == "__main__":
    main()
