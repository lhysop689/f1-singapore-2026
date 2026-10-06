"""Run the whole analysis end to end.

    python run_pipeline.py              download (if needed) -> check -> score -> figures
    python run_pipeline.py --skip-pull  rebuild tables and figures from data/raw only

Steps live in scripts/ and run in numbered order. Downloads are cached, so a
second full run only fetches what is missing.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PULL_STEPS = ["01_pull_sessions.py", "02_pull_corner_speeds.py"]
BUILD_STEPS = ["03_check_data.py", "04_compute_scores.py", "05_make_figures.py"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-pull", action="store_true", help="skip the FastF1 downloads (steps 1-2)")
    args = parser.parse_args()
    steps = BUILD_STEPS if args.skip_pull else PULL_STEPS + BUILD_STEPS
    for step in steps:
        print(f"\n=== {step} ===", flush=True)
        subprocess.run([sys.executable, str(ROOT / "scripts" / step)], check=True)


if __name__ == "__main__":
    main()
