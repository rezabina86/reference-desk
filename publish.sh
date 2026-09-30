#!/usr/bin/env bash
# Rebuild the knowledge site and publish the public half to reza-bina.com/notes.
#
#   ./publish.sh            build, commit, push
#   ./publish.sh --dry-run  build and report what would be committed, change nothing
#
# Two repos are touched: this one (sources + docs/) and the site (public/notes).
# The private build, which carries the day sessions, never leaves this machine.
set -euo pipefail

KNOWLEDGE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE="${SITE_REPO:-$(cd "$KNOWLEDGE/.." && pwd)/reza-bina.com}"
NOTES="$SITE/public/notes/index.html"
DRY_RUN=false
[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

say() { printf '%s\n' "$*"; }
die() { printf 'publish: %s\n' "$*" >&2; exit 1; }

[ -d "$SITE/.git" ] || die "no site repo at $SITE (set SITE_REPO to override)"

# ---------------------------------------------------------------- build
cd "$KNOWLEDGE"
python3 build.py                       # private: everything, stays local
python3 build.py --public              # docs/index.html, the standalone copy
mkdir -p "$(dirname "$NOTES")"
python3 build.py --public --out "$NOTES"

# ------------------------------------------------- refuse to leak the private half
for term in "Day Sessions" "Kündigungsfrist" "<!--private-->"; do
  if grep -qF "$term" "$NOTES"; then
    die "the public build contains \"$term\" — nothing was committed"
  fi
done

# ---------------------------------------------------------------- message
# Name what actually changed, so the site history reads like a changelog.
cd "$KNOWLEDGE"
changed="$(git status --porcelain -- topics template.html build.py \
           | awk '{print $NF}' \
           | sed -n 's|^topics/\([^/]*\)/.*|\1|p' \
           | sort -u | grep -v '^daily$' | paste -sd, - | sed 's/,/, /g' || true)"
if [ -n "$changed" ]; then
  subject="notes: update $changed"
else
  subject="notes: rebuild"
fi

# ---------------------------------------------------------------- knowledge repo
cd "$KNOWLEDGE"
if [ -n "$(git status --porcelain)" ]; then
  if $DRY_RUN; then
    say "knowledge: would commit"; git status --short
  else
    git add -A && git commit -q -m "$subject"
    git remote get-url origin >/dev/null 2>&1 && git push -q origin HEAD && say "knowledge: pushed"
  fi
else
  say "knowledge: nothing to commit"
fi

# ---------------------------------------------------------------- site repo
cd "$SITE"
branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$branch" = "main" ] || die "site repo is on '$branch' — switch to main and run again"

if git diff --quiet -- public/notes/index.html && git diff --cached --quiet -- public/notes/index.html; then
  say "site: notes unchanged, nothing to publish"
  exit 0
fi

if $DRY_RUN; then
  say "site: would commit and push public/notes/index.html as \"$subject\""
  exit 0
fi

git add public/notes/index.html
git commit -q -m "$subject"
git push -q origin main
say "site: pushed — https://reza-bina.com/notes/ updates when the Pages action finishes"
