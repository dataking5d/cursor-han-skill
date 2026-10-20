#!/usr/bin/env bash
# Cursor 汉化助手 —— macOS / Linux
set -u
cd "$(dirname "$0")" || exit 1

echo
echo "=========================================================="
echo "            Cursor 汉化助手"
echo "=========================================================="
echo

PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done

if [ -z "$PY" ]; then
    echo "  [失败] 没有找到 Python。"
    echo
    echo "  macOS 可以用:  brew install python   或   python3.org/downloads"
    echo "  Ubuntu/Debian: sudo apt install python3"
    echo
    exit 1
fi

echo "  使用 $PY 执行汉化..."
echo
"$PY" scripts/cursor_han.py
RC=$?

echo
if [ "$RC" -eq 0 ]; then
    echo "  全部搞定！现在请完全退出 Cursor 再重新打开。"
else
    echo "  汉化过程中有问题，日志在: ${TMPDIR:-/tmp}/cursor-han/cursor-han.log"
fi
echo
exit $RC
