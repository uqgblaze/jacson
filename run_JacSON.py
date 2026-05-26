#!/usr/bin/env python3
"""Run JacSON from project root. Use this when deploying from a ZIP (no line-ending issues)."""
import os
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
script = os.path.join(PROJECT_ROOT, "scripts", "scraper_runner.py")
subprocess.run([sys.executable, script], check=True, cwd=PROJECT_ROOT)
