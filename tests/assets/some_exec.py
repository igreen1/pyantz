#!~/.local/bin/uv run --script $0
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "polars>=1.39.3",
# ]
# ///

import argparse

import polars as pl


def main() -> None:
    """Parse the args.""" 
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    output_file = args.output
    write_file(output_file)


def write_file(output_file: str) -> None:
    """Write a dataframe as "proof" that this ran."""
    print("Hello from some_exec.py!")
    pl.DataFrame(
        {
            "a": [1, 2, 3, 4, 5],
        }
    ).write_parquet(output_file)


if __name__ == "__main__":
    main()
