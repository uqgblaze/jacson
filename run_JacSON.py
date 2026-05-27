#!/usr/bin/env python3
"""Run JacSON from project root. Use this when deploying from a ZIP."""

import argparse
import os
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Run JacSON from project root")
    parser.add_argument(
        "--job-id",
        default=None,
        help="Optional job ID used by JacDash for log naming.",
    )
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.dirname(__file__))
    script = os.path.join(project_root, "scripts", "scraper_runner.py")

    cmd = [sys.executable, script]
    if args.job_id:
        cmd.extend(["--job-id", args.job_id])

    subprocess.run(cmd, check=True, cwd=project_root)


if __name__ == "__main__":
    main()
