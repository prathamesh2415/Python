#!/usr/bin/env bash
# Create a dated folder + blank brief for one reel.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y-%m-%d)"
SLUG="${1:-untitled}"
SLUG="$(echo "$SLUG" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')"
DIR="$ROOT/reels/${STAMP}-${SLUG}"

mkdir -p "$DIR"/{stills,clips,export}
cat > "$DIR/brief.md" <<EOF
# Reel brief — ${STAMP} — ${SLUG}

## Niche
-

## Story one-liner
-

## Why it is shareable
-

## Hook
-

## On-screen cards
1.
2.
3.
4.
5.
6.

## Style lock
-

## Audio plan
-

## Caption draft
-

## Results (fill next day)
- Views 24h:
- Shares:
- Saves:
- Keep / tweak / kill:
EOF

echo "Created $DIR"
echo "Next: fill brief.md, then follow checklists/daily-reel.md"
