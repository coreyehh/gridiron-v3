#!/bin/zsh
# Open GRIDIRON by double-clicking this file in Finder.
set -e
HERE="${0:A:h}"
cd "$HERE"
echo "GRIDIRON — launching private dashboard..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3 and try again."
  read "reply?Press Enter to close..."
  exit 1
fi
if [ ! -x ".venv/bin/python" ]; then
  echo "First-time setup: creating private Python environment..."
  python3 -m venv .venv
fi
if ! .venv/bin/python -c "import streamlit,pandas,cryptography" >/dev/null 2>&1; then
  echo "First-time setup: installing dashboard packages. This may take a few minutes."
  .venv/bin/python -m pip install --disable-pip-version-check streamlit pandas cryptography
fi
echo "Opening GRIDIRON at http://127.0.0.1:8501"
.venv/bin/python -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
echo "Dashboard closed."
read "reply?Press Enter to close..."
