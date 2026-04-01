import io
import sys
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

sys.path.insert(0, "/Users/aditya/Documents/Projects/signal")
sys.modules.setdefault("anthropic", SimpleNamespace(Anthropic=object))

from src.cluster import (  # noqa: E402
    _assign_cluster_ids,
    _apply_repair_mapping,
    _get_bad_cluster_ids,
    _parse_json,
    _rebuild_indices,
    _strip_json_fences,
    _validate_merged_clusters,
    _validate_repair_mapping,
    _validate_raw_clusters,
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
