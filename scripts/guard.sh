#!/usr/bin/env bash
# Blocks publication of infrastructure details, personal data and secrets.
# The patterns themselves are private: they come from GUARD_PRIVATE_PATTERNS (CI secret,
# one extended regex, alternatives joined with "|") and/or a git-ignored .guard-private
# file (one regex per line). Nothing sensitive lives in this script.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

patterns=()
[ -n "${GUARD_PRIVATE_PATTERNS:-}" ] && patterns+=("$GUARD_PRIVATE_PATTERNS")
if [ -f .guard-private ]; then
  while IFS= read -r line; do [ -n "$line" ] && [ "${line:0:1}" != "#" ] && patterns+=("$line"); done < .guard-private
fi
if [ ${#patterns[@]} -eq 0 ]; then
  echo "guard: no private patterns configured (set GUARD_PRIVATE_PATTERNS or create .guard-private)"; exit 1
fi
PATTERN="$(IFS='|'; echo "${patterns[*]}")"
SCOPE=(-- . ':!tests/guard/guard.test.sh')

# Working tree (tracked + staged), case-insensitive. Report file:line only: CI logs are public.
if git grep -qIiE "$PATTERN" "${SCOPE[@]}"; then
  { git grep -nIiE "$PATTERN" "${SCOPE[@]}" || true; } | cut -d: -f1,2
  echo "guard: forbidden string in working tree"; exit 1
fi
# Every commit of HEAD: a string that was committed and later removed is still public.
# History of the branch being published; GUARD_HISTORY_SINCE=<ref> skips commits that were
# already public and reviewed before this guard existed.
if [ -n "${GUARD_HISTORY_SINCE:-}" ] && ! git rev-parse -q --verify "${GUARD_HISTORY_SINCE}^{commit}" >/dev/null; then
  echo "guard: GUARD_HISTORY_SINCE=$GUARD_HISTORY_SINCE does not exist (fetch tags?)"; exit 1
fi
# "--" ends the revisions: a file named HEAD must not turn this into an error and a silent pass.
if ! revs=$(git rev-list "${GUARD_HISTORY_SINCE:+$GUARD_HISTORY_SINCE..}HEAD" --); then
  echo "guard: cannot list the history to scan"; exit 1
fi
# Decide with -q (no pipe): piping into `head` lets SIGPIPE + pipefail turn a hit into a pass.
if [ -n "$revs" ] && git grep -qIiE "$PATTERN" $revs "${SCOPE[@]}"; then
  { git grep -lIiE "$PATTERN" $revs "${SCOPE[@]}" || true; } | sed -n '1,5p' || true
  echo "guard: forbidden string in git history"; exit 1
fi

if [ "${GUARD_SKIP_GITLEAKS:-}" = 1 ]; then
  echo "guard: gitleaks skipped (runs as a separate CI step)"
elif command -v gitleaks >/dev/null; then
  gitleaks git . --no-banner --redact -l warn
elif command -v docker >/dev/null; then
  docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest git /repo --no-banner --redact -l warn
else
  echo "guard: gitleaks not available"; exit 1
fi
echo "guard: OK"
