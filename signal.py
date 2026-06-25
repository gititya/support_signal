from __future__ import annotations

import importlib.util
import sys
import sysconfig
from pathlib import Path


def _load_stdlib_signal() -> None:
    stdlib_signal = Path(sysconfig.get_path("stdlib")) / "signal.py"
    spec = importlib.util.spec_from_file_location(__name__, stdlib_signal)
    module = importlib.util.module_from_spec(spec)
    sys.modules[__name__] = module
    spec.loader.exec_module(module)
    globals().update(module.__dict__)


if __name__ == "signal":
    _load_stdlib_signal()

if __name__ != "signal":
    import argparse
    import os

    import anthropic

    from eval_bucket_golden import main as run_golden_eval
    from src.classify import classify_clusters
    from src.cluster import cluster_complaints
    from src.ingest import load_and_filter
    from src.narrate import generate_pm_brief
    from src.score import score_signals

    DEFAULT_PATTERN = "customers unable to dispute incorrect information on their credit report"
    TAXONOMY_PATH = Path("config/taxonomy/transunion.yaml")

    def _parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="Generate a PM brief from CFPB complaint signals.")
        parser.add_argument(
            "pattern",
            nargs="?",
            default=DEFAULT_PATTERN,
            help="Free-text support pattern to investigate.",
        )
        parser.add_argument(
            "--skip-golden",
            action="store_true",
            help="Skip the golden bucket eval. Use only for local debugging.",
        )
        return parser.parse_args()

    def main() -> int:
        args = _parse_args()
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")

        if not args.skip_golden:
            print("Running golden bucket eval before full brief generation...", flush=True)
            golden_result = run_golden_eval()
            if golden_result != 0:
                print("Golden bucket eval failed; stopping before full run.", flush=True)
                return golden_result

        client = anthropic.Anthropic(api_key=api_key)
        df, metadata = load_and_filter(args.pattern)
        clusters = cluster_complaints(args.pattern, df, client=client, taxonomy_path=TAXONOMY_PATH)
        classify_clusters(clusters, client=client)
        score_signals(clusters, metadata=metadata)
        brief_path = generate_pm_brief(args.pattern, metadata, clusters, df, client=client)
        print(f"Wrote PM brief to {brief_path}", flush=True)
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
