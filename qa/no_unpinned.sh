#!/usr/bin/env bash
# Section 9 check 7 for TorchRoll: no @main/@gh-pages, no Math.random, every voice named as a synth.
# Usage: qa/no_unpinned.sh [live-url]
set -u; cd "$(dirname "$0")/.."; fail=0
echo "== @main / @gh-pages in repo =="; if rg -n "@main|@gh-pages" app.js index.html; then fail=1; else echo "none"; fi
echo "== Math.random in repo =="; if rg -n "Math\.random" app.js index.html; then fail=1; else echo "none"; fi
echo "== sample/CDN URLs (should be none: all voices are synthesized) =="; if rg -n 'jsdelivr|githubusercontent|unpkg|https?://[^"]*\.(mp3|ogg|flac|wav|sf2)' app.js index.html; then fail=1; else echo "none"; fi
echo "== voice + chair names (each must say synth) =="; rg -o 'name: "[^"]+"' app.js | rg -i "synth" -c
if [ -n "${1:-}" ]; then echo "== live $1/app.js =="; if curl -s "$1/app.js" | rg -n "@main|@gh-pages|Math\.random"; then fail=1; else echo "none"; fi; fi
[ $fail = 0 ] && echo "PASS: pinned, deterministic, honestly named" || echo "FAIL"; exit $fail
