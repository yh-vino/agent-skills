#!/usr/bin/env bash
# Verify a component patch's baseline file hashes against the upstream baseline commit,
# and report whether upstream main has changed those files since.
# Usage: check_baseline.sh <compatibility.py> <upstream-git-url> <baseline-commit> <work-dir>
set -euo pipefail

if [ $# -ne 4 ]; then
    echo "usage: $0 <compatibility.py> <upstream-git-url> <baseline-commit> <work-dir>" >&2
    exit 2
fi
COMPAT=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
URL=$2
COMMIT=$3
DIR=$4

[ -f "$COMPAT" ] || { echo "file not found: $COMPAT" >&2; exit 2; }
[ ! -e "$DIR" ] || { echo "work dir already exists: $DIR" >&2; exit 2; }

# BASELINE_FILES is a literal {relative path: sha256} dict in the compatibility module.
EXPECTED=$(python3 -I - "$COMPAT" <<'EOF'
import ast, sys
tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "BASELINE_FILES" for t in node.targets):
        for path, digest in ast.literal_eval(node.value).items():
            print(path, digest)
        break
else:
    sys.exit("BASELINE_FILES not found")
EOF
)

echo "== fetch $URL @ $COMMIT (shallow, LFS content skipped)"
export GIT_LFS_SKIP_SMUDGE=1
git init -q "$DIR"
cd "$DIR"
git fetch -q --depth 1 "$URL" "$COMMIT"
git -c advice.detachedHead=false checkout -q FETCH_HEAD

echo "== baseline hashes"
bad=0
while read -r path digest; do
    actual=$( [ -f "$path" ] && python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],\"rb\").read()).hexdigest())" "$path" || echo missing )
    if [ "$actual" = "$digest" ]; then echo "ok    $path"; else echo "FAIL  $path ($actual)"; bad=1; fi
done <<< "$EXPECTED"

echo "== upstream main vs baseline"
# Fetching main can pull a much larger tree than the baseline and stall, so compare
# blob SHAs through the GitHub API instead.
REPO=$(sed -nE 's#^https://github\.com/([^/]+/[^/.]+)(\.git)?/?$#\1#p' <<< "$URL")
if [ -z "$REPO" ]; then
    echo "skipped: not a github.com URL"
    exit $bad
fi
echo "main is $(gh api "repos/$REPO/commits/main" --jq '.sha[:7]')"
while read -r path _; do
    upstream=$(gh api "repos/$REPO/contents/$path?ref=main" --jq .sha 2>/dev/null || echo missing)
    if [ "$upstream" = "$(git rev-parse "HEAD:$path" 2>/dev/null)" ]; then
        echo "same     $path"
    else
        echo "changed  $path"
    fi
done <<< "$EXPECTED"
exit $bad
