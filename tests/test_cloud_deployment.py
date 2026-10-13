from __future__ import annotations

import hashlib
import io
import json
import math
import tarfile
from pathlib import Path
from urllib.error import URLError

import pytest

from demo import cloud_artifacts


ROOT = Path(__file__).resolve().parents[1]


def _archive(payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        member = tarfile.TarInfo(cloud_artifacts.SCIFACT_CORPUS_MEMBER)
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    return buffer.getvalue()


def test_verified_download_extracts_only_expected_member(tmp_path, monkeypatch) -> None:
    corpus = b'{"doc_id": 1, "title": "t", "abstract": ["a"], "structured": false}\n'
    archive = _archive(corpus)
    monkeypatch.delenv("SCIFACT_CORPUS_PATH", raising=False)
    monkeypatch.setattr(cloud_artifacts, "SCIFACT_ARCHIVE_BYTES", len(archive))
    monkeypatch.setattr(cloud_artifacts, "SCIFACT_ARCHIVE_SHA256", hashlib.sha256(archive).hexdigest())
    monkeypatch.setattr(cloud_artifacts, "SCIFACT_CORPUS_BYTES", len(corpus))
    monkeypatch.setattr(cloud_artifacts, "SCIFACT_CORPUS_SHA256", hashlib.sha256(corpus).hexdigest())

    verified = cloud_artifacts.ensure_scifact_corpus(
        tmp_path / "repo",
        cache_dir=tmp_path / "cache",
        opener=lambda *_args, **_kwargs: io.BytesIO(archive),
    )
    assert verified.path.read_bytes() == corpus
    assert verified.source == "audited official download"
    assert not list((tmp_path / "cache").glob("*.tar.gz"))


def test_download_failure_is_user_readable_and_has_no_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("SCIFACT_CORPUS_PATH", raising=False)

    def fail(*_args, **_kwargs):
        raise URLError("offline")

    with pytest.raises(cloud_artifacts.ArtifactDownloadError, match="official SciFact"):
        cloud_artifacts.ensure_scifact_corpus(
            tmp_path / "repo", cache_dir=tmp_path / "cache", opener=fail
        )
    assert not (tmp_path / "cache/corpus.jsonl").exists()


def test_verified_cache_survives_restart_without_network(tmp_path, monkeypatch) -> None:
    corpus = b'{"doc_id": 1, "title": "t", "abstract": ["a"], "structured": false}\n'
    archive = _archive(corpus)
    monkeypatch.delenv("SCIFACT_CORPUS_PATH", raising=False)
    monkeypatch.setattr(cloud_artifacts, "SCIFACT_ARCHIVE_BYTES", len(archive))
    monkeypatch.setattr(cloud_artifacts, "SCIFACT_ARCHIVE_SHA256", hashlib.sha256(archive).hexdigest())
    monkeypatch.setattr(cloud_artifacts, "SCIFACT_CORPUS_BYTES", len(corpus))
    monkeypatch.setattr(cloud_artifacts, "SCIFACT_CORPUS_SHA256", hashlib.sha256(corpus).hexdigest())
    cache = tmp_path / "cache"
    first = cloud_artifacts.ensure_scifact_corpus(
        tmp_path / "repo", cache_dir=cache,
        opener=lambda *_args, **_kwargs: io.BytesIO(archive),
    )

    def offline(*_args, **_kwargs):
        raise AssertionError("restart must use the verified disk cache")

    second = cloud_artifacts.ensure_scifact_corpus(
        tmp_path / "repo", cache_dir=cache, opener=offline
    )
    assert first.path == second.path
    assert second.source == "verified runtime cache"


def test_corrupt_cached_corpus_is_rejected_before_network(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("SCIFACT_CORPUS_PATH", raising=False)
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "corpus.jsonl").write_bytes(b"not the audited corpus")
    called = False

    def should_not_run(*_args, **_kwargs):
        nonlocal called
        called = True
        return io.BytesIO()

    with pytest.raises(cloud_artifacts.ArtifactIntegrityError, match="size check failed"):
        cloud_artifacts.ensure_scifact_corpus(
            tmp_path / "repo", cache_dir=cache, opener=should_not_run
        )
    assert called is False


def test_frozen_numeric_models_are_verified_and_finite() -> None:
    spec = cloud_artifacts.load_verified_numeric_models(ROOT)
    rows = [
        {
            "F1_decision_confidence": 0.8,
            "F2_support_contradict_margin": 0.4,
            "F3_is_contradict": 0.0,
            "F3_is_no_relation": 0.0,
            "F4_bm25_top2_normalized_margin": 0.1,
            "F5_evidence_conflict_rate": 0.2,
        },
        {
            "F1_decision_confidence": 0.7,
            "F2_support_contradict_margin": 0.05,
            "F3_is_contradict": 0.0,
            "F3_is_no_relation": 1.0,
            "F4_bm25_top2_normalized_margin": 0.3,
            "F5_evidence_conflict_rate": 0.8,
        },
    ]
    scores = cloud_artifacts.score_frozen_models(spec, rows)
    assert set(scores) == {"B1", "EARS"}
    assert all(math.isfinite(value) and 0.0 <= value <= 1.0 for values in scores.values() for value in values)
    assert scores["B1"] == pytest.approx(
        [0.36627805306409594, 0.8301963616900297], abs=1e-15
    )
    assert scores["EARS"] == pytest.approx(
        [0.3654854905855412, 0.5932802392000984], abs=1e-15
    )


def test_public_model_manifest_preserves_original_serialization_gate() -> None:
    manifest = json.loads(
        (ROOT / "demo/frozen_parameters/final_model_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "FINAL_MODELS_FROZEN_BEFORE_TEST_ACCESS"
    assert manifest["serialization_consistency"]["passed"] is True
    assert manifest["serialization_consistency"]["tolerance"] == 1e-12
    assert manifest["internal_test_content_accessed_before_freeze"] is False


def test_cloud_artifact_manifest_matches_deployment_files() -> None:
    manifest = json.loads((ROOT / "CLOUD_ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["scifact"]["included_in_repository"] is False
    assert manifest["scifact"]["corpus_sha256"] == cloud_artifacts.SCIFACT_CORPUS_SHA256
    assert manifest["scifact"]["archive_sha256"] == cloud_artifacts.SCIFACT_ARCHIVE_SHA256
    for record in manifest["files"]:
        path = ROOT / record["path"]
        assert path.stat().st_size == record["bytes"]
        assert cloud_artifacts.sha256_file(path) == record["sha256"]
