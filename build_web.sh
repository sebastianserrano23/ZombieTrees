#!/usr/bin/env bash
# Build the browser (WebAssembly) version of Zombie Trees with pygbag.
#
#   ./build_web.sh
#
# Produces build/web.zip — upload that to itch.io as an HTML project.
# Requires: pip install pygbag
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-.venv/bin/python}
if ! "$PY" -c "import pygbag" 2>/dev/null; then
    echo "pygbag is not installed. Run: $PY -m pip install pygbag"
    exit 1
fi

# pygbag packages the whole folder the game lives in, so build from a clean copy
# that has no .venv or build output in it (the folder name becomes the app name).
rm -rf build/zombietrees build/web build/web.zip
mkdir -p build/zombietrees
rsync -a --exclude __pycache__ main.py zombietrees build/zombietrees/

"$PY" -m pygbag --build --archive --ume_block 0 \
    --title "Zombie Trees" --width 960 --height 600 \
    build/zombietrees/main.py

cp build/zombietrees/build/web.zip build/web.zip
cp -R build/zombietrees/build/web build/web
echo
echo "Done. Upload build/web.zip to itch.io (Kind of project: HTML)."
echo "To try it locally first: $PY -m http.server --directory build/web 8000"
