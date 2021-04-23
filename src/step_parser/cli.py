import argparse
import time

from stepchart import batch_analysis


def step_parser_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("target_dir")
    parser.add_argument("output_file", default=f"step_parser_output_{int(time.time())}.csv")
    parser.add_argument("--raise-on-unknown-failure", action="store_true")
    args = parser.parse_args()

    batch_analysis(args.target_dir, args.output_file, args.raise_on_unknown_failure)


if __name__ == "__main__":
    step_parser_cli()
