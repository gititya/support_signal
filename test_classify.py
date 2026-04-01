import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, "/Users/aditya/Documents/Projects/signal")
sys.modules.setdefault("anthropic", SimpleNamespace(Anthropic=object))

from src.classify import (  # noqa: E402
    CONFIDENCE,
    _load_company_config,
    _validate_classifications,
    classify_clusters,
)

# Load the real TransUnion config for use in tests
_TU_CONFIG = _load_company_config("transunion")
_TU_CATEGORIES = _TU_CONFIG["categories"]
_TU_VALID_TYPES = set(_TU_CATEGORIES.keys())


def _make_clusters(n=3):
    return [
        {
            "name": f"Theme {i}",
            "description": f"Description {i}",
            "hypotheses": ["This may indicate a system issue."],
            "complaint_count": 10 + i,
            "complaint_indices": list(range(i * 10, i * 10 + 10)),
        }
        for i in range(n)
    ]


def _make_valid_result(n=3):
    types = ["Defect", "UX Friction", "Knowledge Gap"]
    return [
        {"i": i, "signal_type": types[i % len(types)], "rationale": f"Because {i}."}
        for i in range(n)
    ]


class ClassifyValidationTests(unittest.TestCase):

    def test_validate_accepts_valid_result(self):
        _validate_classifications(_make_valid_result(3), 3, _TU_VALID_TYPES)

    def test_validate_rejects_wrong_count(self):
        with self.assertRaisesRegex(ValueError, "expected 3"):
            _validate_classifications(_make_valid_result(2), 3, _TU_VALID_TYPES)

    def test_validate_rejects_invalid_index(self):
        result = [{"i": 99, "signal_type": "Defect", "rationale": "x"}]
        with self.assertRaisesRegex(ValueError, "invalid index"):
            _validate_classifications(result, 1, _TU_VALID_TYPES)

    def test_validate_rejects_unknown_signal_type(self):
        result = [{"i": 0, "signal_type": "Bug", "rationale": "x"}]
        with self.assertRaisesRegex(ValueError, "unknown signal_type"):
            _validate_classifications(result, 1, _TU_VALID_TYPES)

    def test_validate_rejects_empty_rationale(self):
        result = [{"i": 0, "signal_type": "Defect", "rationale": ""}]
        with self.assertRaisesRegex(ValueError, "missing rationale"):
            _validate_classifications(result, 1, _TU_VALID_TYPES)

    def test_transunion_config_has_four_categories(self):
        self.assertEqual(len(_TU_CATEGORIES), 4)
        self.assertIn("Defect", _TU_CATEGORIES)
        self.assertIn("UX Friction", _TU_CATEGORIES)
        self.assertIn("Knowledge Gap", _TU_CATEGORIES)
        self.assertIn("Monetization Opportunity", _TU_CATEGORIES)

    def test_transunion_config_categories_have_definitions_and_examples(self):
        for name, meta in _TU_CATEGORIES.items():
            self.assertIn("definition", meta, f"{name} missing definition")
            self.assertIsInstance(meta["definition"], str)
            self.assertIn("examples", meta, f"{name} missing examples")
            self.assertIsInstance(meta["examples"], list)
            self.assertGreater(len(meta["examples"]), 0, f"{name} has no examples")

    def test_confidence_is_directional(self):
        self.assertEqual(CONFIDENCE, "Directional")

    def test_classify_clusters_mutates_in_place(self):
        """classify_clusters with a stubbed client appends the right fields."""
        clusters = _make_clusters(3)
        result_data = _make_valid_result(3)

        class FakeContent:
            text = __import__("json").dumps(result_data)

        class FakeResponse:
            stop_reason = "end_turn"
            content = [FakeContent()]

        class FakeClient:
            class messages:
                @staticmethod
                def create(**kwargs):
                    return FakeResponse()

        classify_clusters(clusters, client=FakeClient())

        for c in clusters:
            self.assertIn("signal_type", c)
            self.assertIn("classification_rationale", c)
            self.assertIn("recommended_audience", c)
            self.assertEqual(c["confidence"], "Directional")
            self.assertIn(c["signal_type"], _TU_VALID_TYPES)

    def test_classify_clusters_returns_empty_unchanged(self):
        result = classify_clusters([], client=None)
        self.assertEqual(result, [])

    def test_load_company_config_raises_for_unknown_slug(self):
        with self.assertRaises(FileNotFoundError):
            _load_company_config("nonexistent_company")


if __name__ == "__main__":
    unittest.main()
