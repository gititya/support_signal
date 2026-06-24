import unittest

from src.score import CONFIDENCE, score_signal, score_signals


class ScoreTests(unittest.TestCase):
    def test_high_volume_defect_scores_high_with_directional_confidence(self):
        signal = {
            "complaint_count": 300,
            "signal_type": "Defect",
            "evidence_bucket_name": "Investigation Did Not Fix Error",
            "supporting_indices": [1, 2, 3],
        }
        metadata = {"date_start": "2026-01-01", "date_end": "2026-03-01"}

        score_signal(signal, metadata)

        self.assertEqual(signal["severity"], "High")
        self.assertEqual(signal["volume_label"], "High volume")
        self.assertEqual(signal["confidence"], CONFIDENCE)
        self.assertIn("no product telemetry", signal["scoring_rationale"])

    def test_other_bucket_reduces_severity(self):
        signal = {
            "complaint_count": 100,
            "signal_type": "Knowledge Gap",
            "evidence_bucket_name": "Other/Unclassified",
            "is_other_bucket": True,
            "supporting_indices": [1],
        }

        score_signal(signal, {})

        self.assertEqual(signal["severity"], "Low")
        self.assertEqual(signal["volume_label"], "Medium volume")

    def test_score_signals_mutates_all(self):
        signals = [
            {"complaint_count": 1, "signal_type": "UX Friction"},
            {"complaint_count": 250, "signal_type": "Defect"},
        ]

        result = score_signals(signals, {})

        self.assertIs(result, signals)
        self.assertTrue(all("scoring_rationale" in signal for signal in signals))


if __name__ == "__main__":
    unittest.main()
