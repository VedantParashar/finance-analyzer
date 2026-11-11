"""Entry point for Streamlit Community Cloud: set "Main file path" to this file. See DEPLOY.md.

Locally, keep using: uv run --env-file .env finance-analyzer
"""

import sys
from pathlib import Path

# The hosted app runs from a checkout of the repo, where the package in src/ may not be installed.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finance_analyzer.app import run  # noqa: E402

run()
