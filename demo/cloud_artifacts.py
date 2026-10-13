"""Verified runtime artifacts for the public Streamlit demo.

The corpus is downloaded only from the Phase 0 audited SciFact archive and is
accepted only after both archive and extracted-file SHA-256 checks pass. Risk
models are evaluated from the frozen lossless numeric specification; no pickle
or joblib deserialization occurs in the public app.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np


SCIFACT_ARCHIVE_URL = "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
SCIFACT_ARCHIVE_SHA256 = "11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be"
SCIFACT_ARCHIVE_BYTES = 3_115_079
SCIFACT_CORPUS_SHA256 = "b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62"
SCIFACT_CORPUS_BYTES = 8_307_875
SCIFACT_CORPUS_MEMBER = "data/corpus.jsonl"
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024

MODEL_MANIFEST_SHA256 = "469cf52a4924a356b3fe224526cd444d82728d0534d7cb4d89848bc923449ea3"
MODEL_NUMERIC_SPEC_SHA256 = "c472f5b0f6035ca1fb70154efc4f76798681db8d5b8d2084f831cb6b62d9d90b"


class CloudArtifactError(RuntimeError):
    """Base error whose message is safe to show in the public interface."""


class ArtifactIntegrityError(CloudArtifactError):
    """Raised when a local or downloaded artifact fails verification."""


class ArtifactDownloadError(CloudArtifactError):
    """Raised when the official artifact cannot be downloaded."""


@dataclass(frozen=True)
class VerifiedCorpus:
    path: Path
    source: str
    sha256: str
    size_bytes: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_file(path: Path, *, expected_sha256: str, expected_bytes: int, label: str) -> None:
    if not path.is_file():
        raise ArtifactIntegrityError(f"{label} is missing: {path.name}")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise ArtifactIntegrityError(
            f"{label} size check failed (expected {expected_bytes:,} bytes; found {actual_bytes:,})."
        )
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise ArtifactIntegrityError(
            f"{label} SHA-256 check failed; refusing to load unverified bytes."
        )


def _download_verified_corpus(
    target: Path,
    *,
    opener: Callable[..., Any] = urlopen,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    archive_path: Path | None = None
    corpus_temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="scifact-archive-", suffix=".tar.gz", dir=target.parent, delete=False
        ) as archive_temp:
            archive_path = Path(archive_temp.name)
            request = Request(
                SCIFACT_ARCHIVE_URL,
                headers={"User-Agent": "trustworthy-ai-research-lab/1.0"},
            )
            try:
                with opener(request, timeout=60) as response:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        archive_temp.write(chunk)
                        if archive_temp.tell() > MAX_ARCHIVE_BYTES:
                            raise ArtifactIntegrityError(
                                "SciFact download exceeded the audited archive size limit."
                            )
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                raise ArtifactDownloadError(
                    "Could not download the audited official SciFact archive. "
                    "Please retry later or check Streamlit Cloud network access."
                ) from exc

        _verify_file(
            archive_path,
            expected_sha256=SCIFACT_ARCHIVE_SHA256,
            expected_bytes=SCIFACT_ARCHIVE_BYTES,
            label="SciFact archive",
        )

        with tarfile.open(archive_path, mode="r:gz") as archive:
            try:
                member = archive.getmember(SCIFACT_CORPUS_MEMBER)
            except KeyError as exc:
                raise ArtifactIntegrityError(
                    "The verified SciFact archive does not contain data/corpus.jsonl."
                ) from exc
            if not member.isfile() or member.size != SCIFACT_CORPUS_BYTES:
                raise ArtifactIntegrityError("SciFact corpus archive member has an unexpected type or size.")
            source = archive.extractfile(member)
            if source is None:
                raise ArtifactIntegrityError("SciFact corpus could not be read from the archive.")
            with tempfile.NamedTemporaryFile(
                prefix="corpus-", suffix=".jsonl", dir=target.parent, delete=False
            ) as corpus_temp:
                corpus_temp_path = Path(corpus_temp.name)
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    corpus_temp.write(chunk)

        _verify_file(
            corpus_temp_path,
            expected_sha256=SCIFACT_CORPUS_SHA256,
            expected_bytes=SCIFACT_CORPUS_BYTES,
            label="SciFact corpus",
        )
        os.replace(corpus_temp_path, target)
        corpus_temp_path = None
    except CloudArtifactError:
        raise
    except (tarfile.TarError, OSError) as exc:
        raise ArtifactIntegrityError(
            "The SciFact archive could not be safely verified and extracted."
        ) from exc
    finally:
        for temporary in (archive_path, corpus_temp_path):
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def ensure_scifact_corpus(
    root: Path,
    *,
    cache_dir: Path | None = None,
    opener: Callable[..., Any] = urlopen,
) -> VerifiedCorpus:
    """Return a verified corpus, downloading the audited archive when absent."""
    explicit = os.environ.get("SCIFACT_CORPUS_PATH")
    if explicit:
        path = Path(explicit).expanduser().resolve()
        _verify_file(
            path,
            expected_sha256=SCIFACT_CORPUS_SHA256,
            expected_bytes=SCIFACT_CORPUS_BYTES,
            label="Configured SciFact corpus",
        )
        return VerifiedCorpus(path, "configured verified file", SCIFACT_CORPUS_SHA256, SCIFACT_CORPUS_BYTES)

    repository_copy = root / "data/raw/scifact/corpus.jsonl"
    if repository_copy.exists():
        _verify_file(
            repository_copy,
            expected_sha256=SCIFACT_CORPUS_SHA256,
            expected_bytes=SCIFACT_CORPUS_BYTES,
            label="Repository SciFact corpus",
        )
        return VerifiedCorpus(repository_copy, "local verified file", SCIFACT_CORPUS_SHA256, SCIFACT_CORPUS_BYTES)

    runtime_dir = cache_dir or (root / ".cache/scifact")
    cached = runtime_dir / "corpus.jsonl"
    if cached.exists():
        _verify_file(
            cached,
            expected_sha256=SCIFACT_CORPUS_SHA256,
            expected_bytes=SCIFACT_CORPUS_BYTES,
            label="Cached SciFact corpus",
        )
        return VerifiedCorpus(cached, "verified runtime cache", SCIFACT_CORPUS_SHA256, SCIFACT_CORPUS_BYTES)

    _download_verified_corpus(cached, opener=opener)
    return VerifiedCorpus(cached, "audited official download", SCIFACT_CORPUS_SHA256, SCIFACT_CORPUS_BYTES)


def load_verified_numeric_models(root: Path) -> dict[str, Any]:
    artifact_dir = root / "demo/frozen_parameters"
    manifest_path = artifact_dir / "final_model_manifest.json"
    spec_path = artifact_dir / "final_model_numeric_spec.json"
    _verify_file(
        manifest_path,
        expected_sha256=MODEL_MANIFEST_SHA256,
        expected_bytes=3_041,
        label="Frozen model manifest",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded = manifest.get("artifact_sha256", {}).get(
        "models/phase3b/final_model_numeric_spec.json"
    )
    if recorded != MODEL_NUMERIC_SPEC_SHA256:
        raise ArtifactIntegrityError("Frozen manifest does not identify the expected numeric model specification.")
    _verify_file(
        spec_path,
        expected_sha256=MODEL_NUMERIC_SPEC_SHA256,
        expected_bytes=4_151,
        label="Frozen numeric model specification",
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != 1 or spec.get("training_claims") != 329 or spec.get("training_errors") != 175:
        raise ArtifactIntegrityError("Frozen numeric model metadata is inconsistent with Phase 3B.")
    for method in ("B1", "EARS"):
        model = spec.get("methods", {}).get(method)
        if not isinstance(model, dict) or model.get("classes") != [0, 1] or not model.get("converged"):
            raise ArtifactIntegrityError(f"Frozen {method} model metadata is invalid.")
        prep = model["preprocessor"]
        width = len(prep["columns"])
        if not (
            width == len(prep["means"]) == len(prep["scales"])
            == len(prep["standardized"]) == len(model["coefficients"])
        ):
            raise ArtifactIntegrityError(f"Frozen {method} model dimensions are inconsistent.")
        if not all(math.isfinite(float(value)) and float(value) > 0 for value in prep["scales"]):
            raise ArtifactIntegrityError(f"Frozen {method} model contains an invalid scale.")
    return spec


def score_numeric_method(method_spec: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    """Apply the frozen scaler and logistic coefficients without deserialization."""
    prep = method_spec["preprocessor"]
    columns = prep["columns"]
    matrix = np.asarray([[float(row[column]) for column in columns] for row in rows], dtype=float)
    if matrix.shape != (len(rows), len(columns)) or not np.isfinite(matrix).all():
        raise ValueError("Risk features must form a finite matrix with the frozen columns.")
    for index, standardized in enumerate(prep["standardized"]):
        if standardized:
            matrix[:, index] = (
                matrix[:, index] - float(prep["means"][index])
            ) / float(prep["scales"][index])
    logits = matrix @ np.asarray(method_spec["coefficients"], dtype=float)
    logits += float(method_spec["intercept"])
    probabilities = np.empty_like(logits, dtype=float)
    positive = logits >= 0
    probabilities[positive] = 1.0 / (1.0 + np.exp(-logits[positive]))
    exp_values = np.exp(logits[~positive])
    probabilities[~positive] = exp_values / (1.0 + exp_values)
    if not np.isfinite(probabilities).all():
        raise ValueError("Frozen risk scoring produced a non-finite value.")
    return [float(value) for value in probabilities]


def score_frozen_models(spec: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    return {
        method: score_numeric_method(spec["methods"][method], rows)
        for method in ("B1", "EARS")
    }
