import argparse
import os
import sys
import time

pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(pkg_dir)

from step_parser.stepchart import batch_analysis


def step_parser_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("target_dir")
    parser.add_argument("--output", default=f"step_parser_output_{int(time.time())}.csv")
    parser.add_argument("--raise-on-unknown-failure", action="store_true")
    args = parser.parse_args()

    batch_analysis(args.target_dir, args.output, args.raise_on_unknown_failure)


if __name__ == "__main__":
    step_parser_cli()
