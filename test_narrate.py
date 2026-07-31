import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.narrate import generate_pm_brief


class NarrateTests(unittest.TestCase):
    def test_generate_pm_brief_renders_without_live_model(self):
        df = pd.DataFrame([
            {
                "Complaint ID": "123",
                "Date received": "2026-03-01",
                "State": "CA",
                "Issue": "Incorrect information on your report",
                "Sub-issue": "Their investigation did not fix an error on your report",
                "Consumer complaint narrative": "I disputed an inaccurate account and it remained unchanged after the investigation.",
            }
        ])
        signals = [
            {
                "signal_name": "Investigation closure without correction",
                "signal_description": "Consumers say disputes close while the report stays wrong.",
                "bucket_distinction": "This is about a completed investigation that does not correct the error.",
                "evidence_bucket_name": "Investigation Did Not Fix Error",
                "evidence_bucket_description": "Investigation closed but error remained.",
                "signal_type": "Defect",
                "recommended_audience": "Engineering",
                "classification_rationale": "the core correction workflow fails",
                "complaint_count": 12,
                "severity": "Low",
                "volume_label": "Low volume",
                "confidence": "Directional (single source)",
                "source_status": "CFPB complaints only",
                "scoring_rationale": "Low severity because single source.",
                "root_cause_hypotheses": ["This may indicate the investigation closure step is disconnected from report update workflows."],
                "supporting_indices": [0],
            }
        ]
        metadata = {
            "company": "TRANSUNION INTERMEDIATE HOLDINGS, INC.",
            "date_start": "2026-03-01",
            "date_end": "2026-03-01",
            "used_in_analysis": 1,
        }

        with tempfile.TemporaryDirectory(dir="output") as tmp:
            output_path = Path(tmp) / "brief.md"
            result = generate_pm_brief(
                "customers unable to dispute incorrect information",
                metadata,
                signals,
                df,
                client=None,
                output_path=output_path,
            )
            text = result.read_text()

        self.assertIn("## At a glance", text)
        self.assertIn("Directional (single source)", text)
        self.assertIn("Signals found", text)
        self.assertIn("- **Signals found:** 1\n- **Main signal:**", text)
        self.assertIn("## What this is not", text)
        self.assertIn("not a measured incident report", text)

    def test_generate_pm_brief_rejects_uncautious_hypothesis(self):
        df = pd.DataFrame([{"Consumer complaint narrative": "x"}])
        signals = [{
            "signal_name": "Bad signal",
            "root_cause_hypotheses": ["The system is broken."],
        }]

        with self.assertRaisesRegex(ValueError, "cautiously framed"):
            generate_pm_brief("pattern", {}, signals, df, client=None)

    def test_generate_pm_brief_rejects_overclaiming_narration(self):
        df = pd.DataFrame([
            {
                "Complaint ID": "123",
                "Date received": "2026-03-01",
                "State": "CA",
                "Issue": "Incorrect information on your report",
                "Sub-issue": "Their investigation did not fix an error on your report",
                "Consumer complaint narrative": "I disputed an inaccurate account.",
            }
        ])
        signals = [
            {
                "signal_name": "Investigation closure without correction",
                "signal_description": "Consumers say disputes close while the report stays wrong.",
                "bucket_distinction": "This is about a completed investigation that does not correct the error.",
                "evidence_bucket_name": "Investigation Did Not Fix Error",
                "signal_type": "Defect",
                "recommended_audience": "Engineering",
                "classification_rationale": "the core correction workflow fails",
                "complaint_count": 12,
                "severity": "Low",
                "volume_label": "Low volume",
                "confidence": "Directional (single source)",
                "source_status": "CFPB complaints only",
                "scoring_rationale": "Low severity because single source.",
                "root_cause_hypotheses": ["This may indicate the investigation closure step is disconnected from report update workflows."],
                "supporting_indices": [0],
            }
        ]

        class FakeMessage:
            content = __import__("json").dumps({
                "executive_summary": "Consumers correctly execute the process.",
                "recommended_action": "Review cases.",
                "narrative_framing": "This is directional.",
            })

        class FakeChoice:
            finish_reason = "stop"
            message = FakeMessage()

        class FakeResponse:
            choices = [FakeChoice()]

        class FakeClient:
            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        return FakeResponse()

        with self.assertRaisesRegex(ValueError, "overclaimed"):
            generate_pm_brief("pattern", {"used_in_analysis": 1}, signals, df, client=FakeClient())


if __name__ == "__main__":
    unittest.main()
