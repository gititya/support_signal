import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.ingest import DATA_PATH, load_and_filter  # noqa: E402


class LoadAndFilterLiveDataTest(unittest.TestCase):
    def test_load_and_filter_against_real_csv(self):
        if not DATA_PATH.exists():
            self.skipTest(f"{DATA_PATH} not present; skipping live-data test.")

        df, meta = load_and_filter(
            "customers unable to dispute incorrect information on their credit report"
        )
        self.assertGreater(len(df), 0)
        self.assertIn("Consumer complaint narrative", df.columns)

        with self.assertRaises((ValueError, EnvironmentError)):
            load_and_filter("customers complaining about airline baggage fees")


if __name__ == "__main__":
    unittest.main()
