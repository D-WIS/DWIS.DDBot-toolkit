#!/usr/bin/env bash
# Mirror upstream validation code into the portable toolkit package.
# Usage: scripts/sync_ddbot_benchmark.sh [<sha>|--check]
# Change mirrored code in ddbot-benchmark first, then sync it here.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

UPSTREAM_URL="${DDBOT_BENCHMARK_URL:-git@github.com:zl6977/ddbot-benchmark.git}"
BRANCH="master"
CACHE_DIR=".cache/ddbot-benchmark"
PROVENANCE="scripts/.ddbot-benchmark-sync.json"
SOURCE_DIR="src/dwis_validation"
MIRROR_DIR="model-dwis-config/scripts/ddbot_toolkit/validation"

if [ "$#" -gt 1 ]; then
  echo "Usage: $0 [<sha>|--check]" >&2
  exit 2
fi
MODE="sync"
REV="${1:-}"
if [ "$REV" = "--check" ]; then
  MODE="check"
  if [ ! -f "$PROVENANCE" ]; then
    echo "error: $PROVENANCE missing; run $0 first" >&2
    exit 1
  fi
  REV="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["sha"])' "$PROVENANCE")"
elif [[ "$REV" = -* ]]; then
  echo "Usage: $0 [<sha>|--check]" >&2
  exit 2
fi

if [ ! -d "$CACHE_DIR" ]; then
  mkdir -p "$(dirname "$CACHE_DIR")"
  git clone --quiet --bare "$UPSTREAM_URL" "$CACHE_DIR"
fi
# Check the recorded snapshot offline when it is already cached. Sync always
# fetches, so invoking without a SHA follows the current upstream branch tip.
if [ "$MODE" = "sync" ] || ! git --git-dir="$CACHE_DIR" cat-file -e "${REV}^{commit}" 2>/dev/null; then
  git --git-dir="$CACHE_DIR" fetch --quiet --prune "$UPSTREAM_URL" "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
fi
if [ -z "$REV" ]; then
  REV="refs/remotes/origin/$BRANCH"
fi
SHA="$(git --git-dir="$CACHE_DIR" rev-parse --verify "${REV}^{commit}")"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git --git-dir="$CACHE_DIR" archive "$SHA" "$SOURCE_DIR" | tar -x -C "$TMP"
if [ ! -f "$TMP/$SOURCE_DIR/schemas.py" ]; then
  echo "error: validation source missing in ddbot-benchmark @ $SHA" >&2
  exit 1
fi

verify_mirror() {
  if ! diff -r --exclude=__pycache__ --exclude='*.pyc' -q "$TMP/$SOURCE_DIR" "$MIRROR_DIR"; then
    echo "Mirror differs from ddbot-benchmark @ $SHA. Re-run: $0 $SHA" >&2
    return 1
  fi
}

if [ "$MODE" = "check" ]; then
  verify_mirror
  echo "OK: validation mirror matches ddbot-benchmark @ $SHA"
  exit 0
fi

# Replace the complete directory so removed upstream files cannot linger.
python3 - "$TMP/$SOURCE_DIR" "$MIRROR_DIR" <<'PY'
import shutil
import sys
from pathlib import Path

source, destination = map(Path, sys.argv[1:])
if destination.exists():
    shutil.rmtree(destination)
shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
PY
verify_mirror
python3 - "$PROVENANCE" "$UPSTREAM_URL" "$SHA" "$SOURCE_DIR" "$MIRROR_DIR" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

provenance, repo, sha, source, destination = sys.argv[1:]
Path(provenance).write_text(json.dumps({
    "repo": repo,
    "sha": sha,
    "synced_at": datetime.now(timezone.utc).isoformat(),
    "mirror_dirs": {source: destination},
}, indent=2) + "\n")
PY

echo "Synced validation from ddbot-benchmark @ $SHA"
git status --short -- "$MIRROR_DIR" "$PROVENANCE"

# Copy this prompt to a coding agent after every sync. Keep compatibility fixes
# in the toolkit adapter; validation remains an exact upstream mirror.
cat <<'PROMPT'

===== Post-sync repair prompt for a coding agent =====
This repository has just synced upstream validation code using
scripts/sync_ddbot_benchmark.sh. Check and repair the toolkit's compatibility
with the synced validation version, including implementation and verification.

1. Read scripts/.ddbot-benchmark-sync.json, the sync diff, and the result models
   and validation flow in model-dwis-config/scripts/ddbot_toolkit/validation/.
   Inspect how model-dwis-config/scripts/ddbot_toolkit/services.py calls these
   interfaces. Verify compatibility even if the sync produced no code changes.
2. Adapt services.py to actual interface changes and fix other toolkit callers
   if needed. Check renamed fields, nested results, diagnostics, error/warning
   classification, rule results, and graph growth ratios. Preserve the toolkit's
   public JSON contract and repair_suggestions. Do not hide interface mismatches
   behind silent defaults. Respect existing uncommitted changes.
3. Keep validation/ as an exact upstream mirror. Do not edit it directly, modify
   benchmark upstream for toolkit compatibility, or import benchmark's report
   layer. Report any defects in upstream validation separately.
4. Add regression tests where needed for the changes. Cover valid CONFIGs,
   syntax errors, semantic errors, reasoning warnings, and growth ratios.
   Check the current ontology before updating outdated test inputs; do not
   weaken assertions to bypass failures.
5. Run bash scripts/sync_ddbot_benchmark.sh --check, uv run pytest, relevant
   Ruff checks, and a CLI validate smoke test. Report changes, verification
   results, and unresolved issues. If no changes are needed, explain the
   evidence for compatibility. Do not automatically commit or push.
===== End of prompt =====
PROMPT
