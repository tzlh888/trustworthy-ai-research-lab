from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data" / "raw" / "scifact"


def import_script(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit_module = import_script("audit_scifact")
split_module = import_script("make_train_splits")


class Phase0AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = audit_module.audit(DATA)
        cls.train = audit_module.load_jsonl(DATA / "claims_train.jsonl")
        cls.manifest = json.loads((ROOT / "splits" / "train_split_manifest.json").read_text())

    def test_official_row_counts_and_hashes(self):
        self.assertEqual(self.audit["identifiers"]["train"]["rows"], 809)
        self.assertEqual(self.audit["identifiers"]["dev"]["rows"], 300)
        self.assertEqual(self.audit["identifiers"]["test"]["rows"], 300)
        self.assertEqual(self.audit["identifiers"]["corpus"]["rows"], 5183)
        self.assertEqual(
            self.audit["files"]["train"]["sha256"],
            "f4c8fa82d8bd0653a9cc8d61a6ea48c25eacea64e90af5dbf390ebb1b74372f0",
        )

    def test_expected_schema_and_integrity(self):
        self.assertTrue(self.audit["schema"]["matches_expected"])
        for split in ("train", "dev_metadata_only"):
            integrity = self.audit["integrity"][split]
            self.assertEqual(integrity["invalid_document_references"], [])
            self.assertEqual(integrity["invalid_sentence_references"], [])
            self.assertEqual(integrity["invalid_rationale_labels"], [])
            self.assertEqual(integrity["mixed_rationale_label_claim_ids"], [])
        self.assertTrue(self.audit["integrity"]["test_has_only_id_and_claim"])

    def test_dev_and_test_guardrails_are_explicit(self):
        scope = self.audit["audit_scope"]
        self.assertIn("no predictions", scope["dev_restriction"])
        self.assertIn("unlabeled", scope["test_restriction"])
        self.assertNotIn("dev_annotations", self.audit)

    def test_official_cv_must_not_be_used(self):
        cv = self.audit["official_cross_validation"]
        self.assertTrue(cv["each_combined_train_dev_claim_appears_once_as_validation"])
        self.assertTrue(all(fold["contains_raw_dev_claim_ids"] for fold in cv["folds"]))
        self.assertTrue(cv["phase0_policy"].startswith("DO_NOT_USE"))

    def test_raw_empty_evidence_is_not_relabelled_as_abstention(self):
        stats = self.audit["train_annotations"]
        self.assertEqual(stats["empty_evidence_claim_count"], 304)
        self.assertIn("not interchangeable", self.audit["label_semantics"]["warning"])

    def test_outer_split_is_complete_and_disjoint(self):
        splits = self.manifest["outer_splits"]
        id_sets = {name: set(value["claim_ids"]) for name, value in splits.items()}
        self.assertEqual(sum(map(len, id_sets.values())), 809)
        self.assertEqual(set.union(*id_sets.values()), {row["id"] for row in self.train})
        names = sorted(id_sets)
        for index, left in enumerate(names):
            for right in names[index + 1 :]:
                self.assertFalse(id_sets[left] & id_sets[right])

    def test_outer_split_has_no_cited_document_or_duplicate_text_overlap(self):
        row_by_id = {row["id"]: row for row in self.train}
        split_docs = {}
        split_texts = {}
        for name, value in self.manifest["outer_splits"].items():
            split_docs[name] = {
                doc_id for claim_id in value["claim_ids"] for doc_id in row_by_id[claim_id]["cited_doc_ids"]
            }
            split_texts[name] = {
                split_module.normalize_claim(row_by_id[claim_id]["claim"])
                for claim_id in value["claim_ids"]
            }
        names = sorted(split_docs)
        for index, left in enumerate(names):
            for right in names[index + 1 :]:
                self.assertFalse(split_docs[left] & split_docs[right])
                self.assertFalse(split_texts[left] & split_texts[right])

    def test_crossfit_validation_folds_partition_fit(self):
        fit = set(self.manifest["outer_splits"]["fit"]["claim_ids"])
        folds = [
            set(value["claim_ids"])
            for value in self.manifest["crossfit_validation_folds_within_fit"].values()
        ]
        self.assertEqual(set.union(*folds), fit)
        self.assertEqual(sum(map(len, folds)), len(fit))


class UnitTests(unittest.TestCase):
    def test_normalization_is_case_and_punctuation_insensitive(self):
        self.assertEqual(
            audit_module.normalize_claim("A claim, HERE."),
            audit_module.normalize_claim("a claim here"),
        )

    def test_mixed_labels_fail_closed(self):
        row = {
            "id": 1,
            "evidence": {
                "10": [
                    {"label": "SUPPORT", "sentences": [0]},
                    {"label": "CONTRADICT", "sentences": [1]},
                ]
            },
        }
        with self.assertRaises(ValueError):
            audit_module.derived_train_label(row)


if __name__ == "__main__":
    unittest.main()
