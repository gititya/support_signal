import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

sys.path.insert(0, "/Users/aditya/Documents/Projects/signal")
sys.modules.setdefault("anthropic", SimpleNamespace(Anthropic=object))

from src.cluster import (  # noqa: E402
    _assign_cluster_ids,
    _assign_evidence_buckets,
    _assign_evidence_buckets_with_model,
    _apply_repair_mapping,
    _get_bad_cluster_ids,
    _parse_json,
    _rebuild_indices,
    _strip_json_fences,
    _validate_bucket_assignments,
    _validate_signal_synthesis,
    _validate_merged_clusters,
    _validate_repair_mapping,
    _validate_raw_clusters,
    load_taxonomy,
)


def make_raw_batch_clusters():
    batch_one = _assign_cluster_ids(
        [
            {
                "name": "Hard inquiry duplicate",
                "description": "Duplicate hard inquiries appear after shopping for credit.",
                "complaint_indices": [0, 1],
                "hypotheses": ["This may indicate duplicate pulls in the same lending flow."],
            },
            {
                "name": "Dispute blocked",
                "description": "Users cannot submit disputes for incorrect report entries.",
                "complaint_indices": [2],
                "hypotheses": ["Evidence suggests the dispute submission path is failing."],
            },
        ],
        0,
    )
    batch_two = _assign_cluster_ids(
        [
            {
                "name": "Hard inquiry duplicate",
                "description": "Unauthorized hard inquiries appear more than once for a single action.",
                "complaint_indices": [3],
                "hypotheses": ["This pattern is consistent with repeated inquiry creation."],
            },
            {
                "name": "Fraud alert stuck",
                "description": "Fraud alerts remain active or cannot be removed after verification.",
                "complaint_indices": [4, 5],
                "hypotheses": ["This may indicate an alert state sync issue."],
            },
        ],
        1,
    )
    return [batch_one, batch_two]


def make_merged_clusters():
    return [
        {
            "name": f"Theme {idx}",
            "description": f"Description {idx}",
            "cluster_ids": [cluster_id],
            "hypotheses": ["This may indicate a grouped issue."],
        }
        for idx, cluster_id in enumerate(["b00_c00", "b00_c01", "b01_c00", "b01_c01"], start=1)
    ] + [
        {
            "name": f"Theme {idx}",
            "description": f"Description {idx}",
            "cluster_ids": [f"placeholder_{idx}"],
            "hypotheses": ["This may indicate a grouped issue."],
        }
        for idx in range(5, 16)
    ]


def make_taxonomy_yaml() -> str:
    return """
company: TestCo
evidence_buckets:
  - name: Account Information Incorrect
    description: Source category for wrong account details.
    source_combos:
      - issue: Incorrect information on your report
        sub_issue: Account information incorrect
  - name: Investigation Did Not Fix Error
    description: Source category for unresolved dispute investigations.
    source_combos:
      - issue: Problem with a company's investigation into an existing problem
        sub_issue: Their investigation did not fix an error on your report
other_bucket:
  name: Other/Unclassified
  description: Source categories not mapped to a curated evidence bucket.
  source_combos: []
"""


class TaxonomyBucketTests(unittest.TestCase):
    def test_load_taxonomy_rejects_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_taxonomy(Path("/tmp/does-not-exist-taxonomy.yaml"))

    def test_load_taxonomy_rejects_missing_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "taxonomy.yaml"
            path.write_text("""
evidence_buckets:
  - description: Missing name.
    source_combos:
      - issue: Incorrect information on your report
        sub_issue: Account information incorrect
other_bucket:
  name: Other/Unclassified
  description: Other.
  source_combos: []
""")
            with self.assertRaisesRegex(ValueError, "name"):
                load_taxonomy(path)

    def test_assign_evidence_buckets_exact_match_and_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "taxonomy.yaml"
            path.write_text(make_taxonomy_yaml())
            taxonomy = load_taxonomy(path)

        df = pd.DataFrame([
            {
                "Issue": "Incorrect information on your report",
                "Sub-issue": "Account information incorrect",
                "Consumer complaint narrative": "Wrong balance listed.",
            },
            {
                "Issue": "Unexpected issue",
                "Sub-issue": "Unexpected sub issue",
                "Consumer complaint narrative": "Something else happened.",
            },
        ], index=[10, 20])
        buckets = _assign_evidence_buckets(df, taxonomy)

        by_name = {bucket["name"]: bucket for bucket in buckets}
        self.assertEqual(by_name["Account Information Incorrect"]["complaint_indices"], [0])
        self.assertEqual(by_name["Other/Unclassified"]["complaint_indices"], [1])
        self.assertEqual(sum(len(bucket["complaint_indices"]) for bucket in buckets), 2)

    def test_validate_bucket_assignments_rejects_missing_idx(self):
        result = [{"idx": 0, "bucket_index": 0, "assignment_rationale": "fits"}]
        with self.assertRaisesRegex(ValueError, "omitted"):
            _validate_bucket_assignments(result, [0, 1], 2)

    def test_validate_bucket_assignments_rejects_duplicate_idx(self):
        result = [
            {"idx": 0, "bucket_index": 0, "assignment_rationale": "fits"},
            {"idx": 0, "bucket_index": 1, "assignment_rationale": "also fits"},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            _validate_bucket_assignments(result, [0], 2)

    def test_validate_bucket_assignments_rejects_out_of_range_bucket(self):
        result = [{"idx": 0, "bucket_index": 9, "assignment_rationale": "fits"}]
        with self.assertRaisesRegex(ValueError, "invalid bucket_index"):
            _validate_bucket_assignments(result, [0], 2)

    def test_model_assignment_can_override_bad_cfpb_metadata(self):
        taxonomy = {
            "evidence_buckets": [
                {
                    "name": "Improper Report Use",
                    "description": "Unauthorized access, permissible purpose, hard inquiries, or improper use of reports.",
                    "source_combos": [],
                    "is_other": False,
                },
                {
                    "name": "Cross-Bureau Inconsistent Reporting",
                    "description": "Same account or identifier is reported differently across bureaus.",
                    "source_combos": [],
                    "is_other": False,
                },
                {
                    "name": "Other/Unclassified",
                    "description": "Does not fit.",
                    "source_combos": [],
                    "is_other": True,
                },
            ],
        }
        df = pd.DataFrame([
            {
                "Issue": "Improper use of your report",
                "Sub-issue": "Reporting company used your report improperly",
                "Consumer complaint narrative": (
                    "Equifax, Experian, and TransUnion report materially different data "
                    "for the same accounts and personal identifiers despite prior disputes."
                ),
            }
        ])

        class FakeContent:
            text = __import__("json").dumps([
                {
                    "idx": 0,
                    "bucket_index": 1,
                    "assignment_rationale": "Narrative is about cross-bureau inconsistency, not improper report access.",
                }
            ])

        class FakeResponse:
            stop_reason = "end_turn"
            content = [FakeContent()]

        class FakeClient:
            class messages:
                @staticmethod
                def create(**kwargs):
                    return FakeResponse()

        buckets = _assign_evidence_buckets_with_model(
            "customers unable to dispute incorrect information on their credit report",
            df,
            taxonomy,
            FakeClient(),
        )

        self.assertEqual(buckets[0]["complaint_indices"], [])
        self.assertEqual(buckets[1]["complaint_indices"], [0])
        self.assertIn("cross-bureau", buckets[1]["assignment_rationales"][0])

    def test_validate_signal_synthesis_rejects_bucket_name_as_signal(self):
        bucket = {
            "name": "Account Information Incorrect",
            "description": "Source category for wrong account details.",
        }
        result = [{
            "signal_name": "Account Information Incorrect",
            "signal_description": "Users describe unresolved account data problems.",
            "bucket_distinction": "This bucket is about account-level data fields rather than investigation timing.",
            "supporting_indices": [0],
            "root_cause_hypotheses": ["This may indicate dispute evidence is not reflected in report updates."],
        }]
        with self.assertRaisesRegex(ValueError, "identical"):
            _validate_signal_synthesis(result, bucket, [0])

    def test_validate_signal_synthesis_accepts_pm_signal(self):
        bucket = {
            "name": "Account Information Incorrect",
            "description": "Source category for wrong account details.",
        }
        result = [{
            "signal_name": "Dispute evidence appears disconnected from report updates",
            "signal_description": "Consumers say they submit proof but still see the same incorrect account data.",
            "bucket_distinction": "This bucket is about account-level data fields rather than investigation timing.",
            "supporting_indices": [0],
            "root_cause_hypotheses": ["This may indicate evidence review and report update workflows are not closing the loop."],
        }]
        signal = _validate_signal_synthesis(result, bucket, [0])
        self.assertEqual(signal["supporting_indices"], [0])
        self.assertIn("root_cause_hypotheses", signal)

    def test_validate_signal_synthesis_rejects_unsupported_qualifier(self):
        bucket = {
            "name": "Account Information Incorrect",
            "description": "Source category for wrong account details.",
        }
        result = [{
            "signal_name": "Persistent dispute loop failure",
            "signal_description": "Consumers say they submit proof but still see the same incorrect account data.",
            "bucket_distinction": "This bucket is about account-level data fields rather than investigation timing.",
            "supporting_indices": [0],
            "root_cause_hypotheses": ["This may indicate evidence review and report update workflows are not closing the loop."],
        }]
        with self.assertRaisesRegex(ValueError, "unsupported qualifier"):
            _validate_signal_synthesis(result, bucket, [0])


class ClusterValidationTests(unittest.TestCase):
    def test_successful_rebuild_uses_cluster_ids(self):
        batch_clusters = make_raw_batch_clusters()
        merged_clusters = [
            {
                "name": f"Theme {idx}",
                "description": f"Description {idx}",
                "cluster_ids": [cluster_id],
                "hypotheses": ["This may indicate a grouped issue."],
            }
            for idx, cluster_id in enumerate(["b00_c00", "b00_c01", "b01_c00", "b01_c01"], start=1)
        ]
        merged_clusters.extend(
            {
                "name": f"Empty filler {idx}",
                "description": f"Filler description {idx}",
                "cluster_ids": [f"filler_{idx}"],
                "hypotheses": ["This may indicate filler output."],
            }
            for idx in range(5, 16)
        )

        raw_cluster_ids = ["b00_c00", "b00_c01", "b01_c00", "b01_c01"]
        valid_merged = merged_clusters[:4] + [
            {
                "name": f"Pass-through {idx}",
                "description": f"Pass-through description {idx}",
                "cluster_ids": [raw_cluster_ids[(idx - 5) % len(raw_cluster_ids)]],
                "hypotheses": ["This may indicate pass-through output."],
            }
            for idx in range(5, 16)
        ]

        with self.assertRaises(ValueError):
            _validate_merged_clusters(merged_clusters, raw_cluster_ids)

        merged_for_validation = [
            {
                "name": "Inquiry issues",
                "description": "Grouped inquiry-related complaints.",
                "cluster_ids": ["b00_c00"],
                "hypotheses": ["This may indicate grouped inquiry output."],
            },
            {
                "name": "Dispute issues",
                "description": "Grouped dispute-related complaints.",
                "cluster_ids": ["b00_c01"],
                "hypotheses": ["Evidence suggests grouped dispute output."],
            },
            {
                "name": "Repeated inquiry issues",
                "description": "Grouped repeated inquiry complaints.",
                "cluster_ids": ["b01_c00"],
                "hypotheses": ["This pattern is consistent with grouped inquiry output."],
            },
            {
                "name": "Fraud alert issues",
                "description": "Grouped fraud alert complaints.",
                "cluster_ids": ["b01_c01"],
                "hypotheses": ["This may indicate grouped fraud alert output."],
            },
        ]
        merged_for_validation.extend(
            {
                "name": f"Theme {idx}",
                "description": f"Description {idx}",
                "cluster_ids": [f"extra_{idx}"],
                "hypotheses": ["This may indicate extra output."],
            }
            for idx in range(5, 16)
        )

        raw_for_validation = raw_cluster_ids + [f"extra_{idx}" for idx in range(5, 16)]
        _validate_merged_clusters(merged_for_validation, raw_for_validation)

        rebuilt = _rebuild_indices(merged_for_validation[:4], batch_clusters)
        self.assertEqual(rebuilt[0]["complaint_indices"], [0, 1])
        self.assertEqual(rebuilt[1]["complaint_indices"], [2])
        self.assertEqual(rebuilt[2]["complaint_indices"], [3])
        self.assertEqual(rebuilt[3]["complaint_indices"], [4, 5])

    def test_validate_raw_clusters_rejects_missing_cluster_id(self):
        batch_clusters = make_raw_batch_clusters()
        del batch_clusters[0][0]["cluster_id"]
        with self.assertRaisesRegex(ValueError, "cluster_id"):
            _validate_raw_clusters(batch_clusters)

    def test_validate_merged_clusters_rejects_missing_cluster_ids(self):
        raw_cluster_ids = [f"b00_c{idx:02d}" for idx in range(15)]
        merged_clusters = [
            {
                "name": f"Theme {idx}",
                "description": f"Description {idx}",
                "cluster_ids": [cluster_id],
                "hypotheses": ["This may indicate a grouped issue."],
            }
            for idx, cluster_id in enumerate(raw_cluster_ids, start=1)
        ]
        merged_clusters[0]["cluster_ids"] = []

        with self.assertRaisesRegex(ValueError, "cluster_ids"):
            _validate_merged_clusters(merged_clusters, raw_cluster_ids)

    def test_validate_merged_clusters_rejects_duplicate_cluster_id_assignment(self):
        raw_cluster_ids = [f"b00_c{idx:02d}" for idx in range(15)]
        merged_clusters = [
            {
                "name": f"Theme {idx}",
                "description": f"Description {idx}",
                "cluster_ids": [cluster_id],
                "hypotheses": ["This may indicate a grouped issue."],
            }
            for idx, cluster_id in enumerate(raw_cluster_ids, start=1)
        ]
        merged_clusters[1]["cluster_ids"] = [raw_cluster_ids[0]]

        with self.assertRaisesRegex(ValueError, "multiple times"):
            _validate_merged_clusters(merged_clusters, raw_cluster_ids)

    def test_validate_merged_clusters_rejects_cluster_id_count_mismatch(self):
        raw_cluster_ids = [f"b00_c{idx:02d}" for idx in range(16)]
        merged_clusters = [
            {
                "name": f"Theme {idx}",
                "description": f"Description {idx}",
                "cluster_ids": [cluster_id],
                "hypotheses": ["This may indicate a grouped issue."],
            }
            for idx, cluster_id in enumerate(raw_cluster_ids[:-1], start=1)
        ]

        with self.assertRaisesRegex(ValueError, "omitted raw cluster_ids"):
            _validate_merged_clusters(merged_clusters, raw_cluster_ids)

    def test_validate_merged_clusters_rejects_unknown_cluster_id(self):
        raw_cluster_ids = [f"b00_c{idx:02d}" for idx in range(15)]
        merged_clusters = [
            {
                "name": f"Theme {idx}",
                "description": f"Description {idx}",
                "cluster_ids": [cluster_id],
                "hypotheses": ["This may indicate a grouped issue."],
            }
            for idx, cluster_id in enumerate(raw_cluster_ids, start=1)
        ]
        merged_clusters[-1]["cluster_ids"] = ["unknown_cluster"]

        with self.assertRaisesRegex(ValueError, "unknown cluster_ids"):
            _validate_merged_clusters(merged_clusters, raw_cluster_ids)

    def test_rebuild_rejects_empty_theme(self):
        batch_clusters = make_raw_batch_clusters()
        merged_clusters = [
            {
                "name": "Broken theme",
                "description": "Description",
                "cluster_ids": ["b99_c99"],
                "hypotheses": ["This may indicate a grouped issue."],
            }
        ]

        with self.assertRaises(KeyError):
            _rebuild_indices(merged_clusters, batch_clusters)

    def test_over_aggregation_is_warning_only(self):
        raw_cluster_ids = [f"b00_c{idx:02d}" for idx in range(29)]
        merged_clusters = [
            {
                "name": "Dominant theme",
                "description": "Description",
                "cluster_ids": raw_cluster_ids[:15],
                "hypotheses": ["This may indicate a grouped issue."],
            }
        ]
        merged_clusters.extend(
            {
                "name": f"Theme {idx}",
                "description": f"Description {idx}",
                "cluster_ids": [cluster_id],
                "hypotheses": ["This may indicate a grouped issue."],
            }
            for idx, cluster_id in enumerate(raw_cluster_ids[15:], start=2)
        )

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            _validate_merged_clusters(merged_clusters, raw_cluster_ids)

        self.assertIn("over-aggregation", buffer.getvalue())

    def test_singleton_theme_is_warning_only(self):
        raw_cluster_ids = [f"b00_c{idx:02d}" for idx in range(15)]
        merged_clusters = [
            {
                "name": f"Theme {idx}",
                "description": f"Description {idx}",
                "cluster_ids": [cluster_id],
                "hypotheses": ["This may indicate a grouped issue."],
            }
            for idx, cluster_id in enumerate(raw_cluster_ids, start=1)
        ]

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            _validate_merged_clusters(merged_clusters, raw_cluster_ids)

        self.assertIn("under-clustered", buffer.getvalue())

    def test_hypothesis_prefix_mismatch_is_warning_only(self):
        raw_cluster_ids = [f"b00_c{idx:02d}" for idx in range(15)]
        merged_clusters = [
            {
                "name": f"Theme {idx}",
                "description": f"Description {idx}",
                "cluster_ids": [cluster_id],
                "hypotheses": ["Bad prefix hypothesis"],
            }
            for idx, cluster_id in enumerate(raw_cluster_ids, start=1)
        ]

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            _validate_merged_clusters(merged_clusters, raw_cluster_ids)

        self.assertIn("hypothesis prefix mismatch", buffer.getvalue())

    def test_validate_merged_clusters_rejects_non_15_theme_count(self):
        raw_cluster_ids = [f"b00_c{idx:02d}" for idx in range(14)]
        merged_clusters = [
            {
                "name": f"Theme {idx}",
                "description": f"Description {idx}",
                "cluster_ids": [cluster_id],
                "hypotheses": ["This may indicate a grouped issue."],
            }
            for idx, cluster_id in enumerate(raw_cluster_ids, start=1)
        ]

        with self.assertRaisesRegex(ValueError, "exactly 15"):
            _validate_merged_clusters(merged_clusters, raw_cluster_ids)

    def test_strip_json_fences_handles_empty_string(self):
        self.assertEqual(_strip_json_fences(""), "")
        self.assertEqual(_strip_json_fences("   "), "")

    def test_parse_json_rejects_empty_string(self):
        with self.assertRaisesRegex(Exception, "Expecting value"):
            _parse_json("")

    def test_parse_json_rejects_prose(self):
        with self.assertRaisesRegex(Exception, "Expecting value"):
            _parse_json("Here is the repaired output.")

    # --- Repair mapping tests ---

    def test_validate_repair_mapping_rejects_non_list(self):
        with self.assertRaisesRegex(ValueError, "must be a JSON array"):
            _validate_repair_mapping({"cluster_id": "b00_c00", "theme_i": 0}, ["b00_c00"], 2)

    def test_validate_repair_mapping_rejects_duplicate_cluster_id(self):
        repair = [
            {"cluster_id": "b00_c00", "theme_i": 0},
            {"cluster_id": "b00_c00", "theme_i": 1},
        ]
        with self.assertRaisesRegex(ValueError, "more than once"):
            _validate_repair_mapping(repair, ["b00_c00"], 2)

    def test_validate_repair_mapping_rejects_missing_cluster_id(self):
        repair = [
            {"cluster_id": "b00_c00", "theme_i": 0},
        ]
        with self.assertRaisesRegex(ValueError, "did not assign"):
            _validate_repair_mapping(repair, ["b00_c00", "b00_c01"], 2)

    def test_validate_repair_mapping_rejects_unknown_cluster_id(self):
        repair = [
            {"cluster_id": "b99_c99", "theme_i": 0},
        ]
        with self.assertRaisesRegex(ValueError, "unknown cluster_id"):
            _validate_repair_mapping(repair, ["b00_c00"], 2)

    def test_validate_repair_mapping_rejects_invalid_theme_i(self):
        repair = [
            {"cluster_id": "b00_c00", "theme_i": 5},
        ]
        with self.assertRaisesRegex(ValueError, "invalid theme_i"):
            _validate_repair_mapping(repair, ["b00_c00"], 3)

    def test_apply_repair_mapping_removes_bad_and_reassigns(self):
        # b00_c01 is duplicated across theme 0 and theme 1; b00_c02 is missing
        broken = [
            {"name": "Theme A", "description": "desc A", "cluster_ids": ["b00_c00", "b00_c01"], "hypotheses": ["This may indicate A."]},
            {"name": "Theme B", "description": "desc B", "cluster_ids": ["b00_c01"], "hypotheses": ["Evidence suggests B."]},
        ]
        bad = ["b00_c01", "b00_c02"]
        repair = [
            {"cluster_id": "b00_c01", "theme_i": 0},
            {"cluster_id": "b00_c02", "theme_i": 1},
        ]
        result = _apply_repair_mapping(broken, repair, bad)
        self.assertIn("b00_c00", result[0]["cluster_ids"])
        self.assertIn("b00_c01", result[0]["cluster_ids"])
        self.assertNotIn("b00_c01", result[1]["cluster_ids"])
        self.assertIn("b00_c02", result[1]["cluster_ids"])
        # Names/hypotheses unchanged
        self.assertEqual(result[0]["name"], "Theme A")
        self.assertEqual(result[1]["hypotheses"], ["Evidence suggests B."])

    def test_get_bad_cluster_ids_detects_duplicates_and_missing(self):
        merged = [
            {"cluster_ids": ["b00_c00", "b00_c01"]},
            {"cluster_ids": ["b00_c01"]},  # b00_c01 duplicated
        ]
        raw_ids = ["b00_c00", "b00_c01", "b00_c02"]  # b00_c02 missing
        bad = _get_bad_cluster_ids(merged, raw_ids)
        self.assertIn("b00_c01", bad)
        self.assertIn("b00_c02", bad)
        self.assertNotIn("b00_c00", bad)


if __name__ == "__main__":
    unittest.main()
