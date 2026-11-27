"""Create a pending (not submitted) GitHub review from a JSON spec.

Usage: python3 post_pending_review.py <review.json> [--dry-run]

Spec: {"repo": "owner/name", "pr": 19, "head": "<sha>", "body": "...",
       "comments": [{"path": "...", "line": 14, "body": "..."}]}
"""
import json
import re
import subprocess
import sys


def commentable_lines(repo, pr):
    """Map each changed path to the new-side line numbers covered by its diff hunks."""
    done = subprocess.run(["gh", "api", "--paginate", f"repos/{repo}/pulls/{pr}/files",
                           "--jq", ".[] | {filename, patch}"],
                          capture_output=True, text=True)
    if done.returncode:
        sys.exit(f"cannot list PR files: {done.stderr}")
    lines = {}
    for row in done.stdout.splitlines():
        entry = json.loads(row)
        covered = lines.setdefault(entry["filename"], set())
        for start, count in re.findall(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", entry.get("patch") or "", re.M):
            start = int(start)
            covered.update(range(start, start + int(count or 1)))
    return lines


def graphql(query, **variables):
    payload = json.dumps({"query": query, "variables": variables})
    for _ in range(3):
        done = subprocess.run(["gh", "api", "graphql", "--input", "-"],
                              input=payload, capture_output=True, text=True)
        if done.returncode == 0:
            break
    result = json.loads(done.stdout or "{}")
    if done.returncode or result.get("errors"):
        sys.exit(f"graphql failed: {result.get('errors') or done.stderr}")
    return result["data"]


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    owner, name = spec["repo"].split("/")

    pr = graphql("""
        query($owner: String!, $name: String!, $number: Int!) {
          viewer { login }
          repository(owner: $owner, name: $name) {
            pullRequest(number: $number) {
              id headRefOid
              reviews(states: PENDING, first: 10) { nodes { author { login } url } }
            }
          }
        }""", owner=owner, name=name, number=spec["pr"])
    login = pr["viewer"]["login"]
    pr = pr["repository"]["pullRequest"]

    if not pr["headRefOid"].startswith(spec["head"]):
        sys.exit(f"PR head is {pr['headRefOid'][:8]}, spec expects {spec['head'][:8]}; re-check anchors")
    for review in pr["reviews"]["nodes"]:
        if review["author"]["login"] == login:
            sys.exit(f"{login} already has a pending review: {review['url']}; submit or delete it first")

    covered = commentable_lines(spec["repo"], spec["pr"])
    outside = [f"{c['path']}:{c['line']}" for c in spec["comments"]
               if c["line"] not in covered.get(c["path"], ())]
    if outside:
        sys.exit("lines outside the PR diff (GitHub would reject them): " + ", ".join(outside))

    threads = [{"path": c["path"], "line": c["line"], "side": "RIGHT", "body": c["body"]}
               for c in spec["comments"]]
    if "--dry-run" in sys.argv:
        for t in threads:
            print(f"  {t['path']}:{t['line']}  {t['body'][:50]}")
        print(f"dry run ok: head {pr['headRefOid'][:8]}, {len(threads)} comments, nothing created")
        return
    review = graphql("""
        mutation($pr: ID!, $body: String!, $threads: [DraftPullRequestReviewThread]) {
          addPullRequestReview(input: {pullRequestId: $pr, body: $body, threads: $threads}) {
            pullRequestReview { state url body commit { oid } comments(first: 100) { nodes { path line body } } }
          }
        }""", pr=pr["id"], body=spec["body"], threads=threads)["addPullRequestReview"]["pullRequestReview"]

    print(f"state: {review['state']} | commit: {review['commit']['oid'][:8]} | url: {review['url']}")
    for c in review["comments"]["nodes"]:
        print(f"  {c['path']}:{c['line']}  {c['body'][:50]}")
    print(f"comments: {len(review['comments']['nodes'])}/{len(threads)}")
    print("body (paste into 'Finish your review' before submitting):")
    print(review["body"])


if __name__ == "__main__":
    main()
