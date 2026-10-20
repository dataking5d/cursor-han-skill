#!/usr/bin/env bash
# Cursor Hanhua Assistant (macOS / Linux)
# NOTE: ASCII only on purpose. All Chinese messages come from the
# Python script, which handles UTF-8 correctly everywhere.
set -u
cd "$(dirname "$0")" || exit 1

echo
echo "=========================================================="
echo "             Cursor Hanhua Assistant"
echo "=========================================================="
echo

PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done

if [ -z "$PY" ]; then
    echo "  [FAILED] Python was not found."
    echo
    echo "  macOS :  brew install python   (or https://www.python.org/downloads/)"
    echo "  Debian: sudo apt install python3"
    echo
    exit 1
fi

echo "  Running with $PY ..."
echo
"$PY" scripts/cursor_han.py
RC=$?

echo
if [ "$RC" -eq 0 ]; then
    echo "  All done! Now QUIT Cursor completely, then open it again."
else
    echo "  Something went wrong. Please share the output above."
    echo "  Log: ${TMPDIR:-/tmp}/cursor-han/cursor-han.log"
fi
echo
exit $RC
