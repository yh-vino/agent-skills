#!/usr/bin/env bash
# Apply a model-example patch to its upstream baseline and run basic checks.
# Usage: check_patch.sh <patch> <upstream-git-url> <baseline-commit> <work-dir> [<python-version, e.g. 3.10>]
set -euo pipefail

if [ $# -lt 4 ] || [ $# -gt 5 ]; then
    echo "usage: $0 <patch> <upstream-git-url> <baseline-commit> <work-dir> [<python-version>]" >&2
    exit 2
fi
PATCH=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
URL=$2
COMMIT=$3
DIR=$4
PYVER=${5:-}

[ -f "$PATCH" ] || { echo "patch not found: $PATCH" >&2; exit 2; }
[ ! -e "$DIR" ] || { echo "work dir already exists: $DIR" >&2; exit 2; }

echo "== fetch $URL @ $COMMIT (shallow, LFS content skipped)"
# A full clone with LFS content takes minutes; patches normally do not touch LFS files.
# If one does, apply fails on that file and the baseline needs `git lfs pull`.
export GIT_LFS_SKIP_SMUDGE=1
git init -q "$DIR"
cd "$DIR"
git fetch -q --depth 1 "$URL" "$COMMIT"
git -c advice.detachedHead=false checkout -q FETCH_HEAD

echo "== apply"
git apply --check "$PATCH"
git apply "$PATCH"
git apply --check --reverse "$PATCH"
echo "applies and reverse-applies cleanly"

echo "== files"
git add -A
git diff --cached --name-status | awk '
    {n[$1]++; print}
    END {printf "added %d, modified %d, deleted %d\n", n["A"], n["M"], n["D"]}'

echo "== python syntax checks (target: ${PYVER:-local python})"
PYCHECK=$(cat <<'EOF'
import ast, sys
version = tuple(map(int, sys.argv[1].split("."))) if sys.argv[1] else None
bad = 0
for path in sys.stdin.read().split():
    try:
        ast.parse(open(path, encoding="utf-8").read(), path, feature_version=version)
    except SyntaxError as e:
        bad += 1
        print("FAIL", path, e)
print("python checks:", "failed" if bad else "ok")
sys.exit(1 if bad else 0)
EOF
)
git diff --cached --name-only --diff-filter=AM -- '*.py' | python3 -c "$PYCHECK" "$PYVER"
