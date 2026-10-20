#!/usr/bin/env bash
# Runs scripts/guard.sh against throw-away copies of the repo.
set -uo pipefail
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail=0
copy() { cd "$T"; rm -rf "$T/r"; rsync -a --exclude node_modules --exclude dist --exclude .guard-private "$SRC/" "$T/r/"; cd "$T/r"; rm -rf .git; git init -q; git add -A; git -c user.name=t -c user.email=t@t commit -qm base; mkdir -p src; }
expect() { # expect <pass|fail> <name> [env...]
  local want=$1 name=$2; shift 2
  if env "$@" GUARD_SKIP_GITLEAKS=1 bash scripts/guard.sh >/dev/null 2>&1; then got=pass; else got=fail; fi
  if [ "$got" = "$want" ]; then echo "ok   - $name"; else echo "FAIL - $name (wanted $want, got $got)"; fail=1; fi
}
P='GUARD_PRIVATE_PATTERNS=placeholder-street|192\.168\.'

copy; expect pass "clean tree passes"                                  "$P"
copy; expect fail "no private patterns configured -> fails"
copy; echo 'host: 192.168.0.1' > src/x.txt; git add -A
      expect fail "internal IP in tree is caught"                      "$P"
copy; echo 'Placeholder-Street 1' > src/x.txt; git add -A
      expect fail "private pattern caught case-insensitively"          "$P"
copy; echo 'placeholder-street' > src/x.txt; git add -A; git -c user.name=t -c user.email=t@t commit -qm plant; git rm -q src/x.txt; git -c user.name=t -c user.email=t@t commit -qm revert
      expect fail "string committed then removed is caught in history" "$P"
copy; printf 'placeholder-street\n' > .guard-private; echo 'placeholder-street' > src/x.txt; git add src/x.txt
      expect fail "local .guard-private pattern catches planted string"
copy; for i in $(seq 1 12); do echo "placeholder-street $i" > "src/p$i.txt"; git add -A; git -c user.name=t -c user.email=t@t commit -qm "plant $i"; done; git rm -q src/p*.txt; git -c user.name=t -c user.email=t@t commit -qm revert
      expect fail "many history matches are still caught (no SIGPIPE false pass)" "$P"
copy; git checkout -qb other; echo 'placeholder-street' > src/x.txt; git add -A; git -c user.name=t -c user.email=t@t commit -qm plant; git checkout -q -; git branch -q -f published HEAD
      expect pass "only the published branch history is scanned, not other local branches" "$P"
copy; echo placeholder-street > src/old.txt; git add -A; git -c user.name=t -c user.email=t@t commit -qm old; git tag base; git rm -q src/old.txt; git -c user.name=t -c user.email=t@t commit -qm clean
      expect pass "history before GUARD_HISTORY_SINCE is not scanned" "$P" GUARD_HISTORY_SINCE=base
copy; git tag base; echo placeholder-street > src/new.txt; git add -A; git -c user.name=t -c user.email=t@t commit -qm new; git rm -q src/new.txt; git -c user.name=t -c user.email=t@t commit -qm clean
      expect fail "history after GUARD_HISTORY_SINCE is still scanned" "$P" GUARD_HISTORY_SINCE=base
copy; expect fail "missing GUARD_HISTORY_SINCE ref is an error, not a silent pass" "$P" GUARD_HISTORY_SINCE=no-such-tag
copy; mkdir -p docs/superpowers; echo placeholder-street > docs/superpowers/note.md; git add -A
      expect fail "docs/superpowers is scanned too" "$P"
copy; echo placeholder-street > src/x.txt; git add -A; git -c user.name=t -c user.email=t@t commit -qm plant; git rm -q src/x.txt; : > HEAD; git add HEAD; git -c user.name=t -c user.email=t@t commit -qm "revert, add a file named HEAD"
      expect fail "a file named HEAD does not switch the history scan off" "$P"
copy; echo 'Placeholder-Street 1' > src/x.txt; git add -A
      out=$(env "$P" GUARD_SKIP_GITLEAKS=1 bash scripts/guard.sh 2>&1)
      if echo "$out" | grep -qi 'placeholder-street'; then echo "FAIL - report prints the matched text"; fail=1
      elif echo "$out" | grep -q 'src/x.txt'; then echo "ok   - report names the file, not the matched text"
      else echo "FAIL - report does not name the file"; fail=1; fi
if [ -f "$SRC/.guard-private" ]; then
  copy; cp "$SRC/.guard-private" .
  expect pass "current tree is clean against the real private patterns"
fi
cd "$SRC"
[ $fail = 0 ] && echo "guard tests: OK"; exit $fail
