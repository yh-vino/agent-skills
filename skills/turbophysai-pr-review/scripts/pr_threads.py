"""List every review thread of a PR with its state, for re-reviews. Read-only.

Usage: python3 pr_threads.py <pr> [<owner/name>]   (default repo: HYGON-AI/TurboPhysAI)

Per thread: resolved / outdated state, anchor, who opened it, and the last reply
(or "no reply"). Also prints the viewer's unsubmitted pending review, if any.
"""
import json
import subprocess
import sys

QUERY = """
query($owner: String!, $name: String!, $number: Int!, $after: String) {
  viewer { login }
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      headRefOid mergeable
      reviews(states: PENDING, first: 10) { nodes { author { login } url } }
      reviewThreads(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved isOutdated path line originalLine
          comments(first: 100) { nodes { author { login } body createdAt url } }
        }
      }
    }
  }
}"""


def fetch(owner, name, number, after=None):
    payload = json.dumps({"query": QUERY, "variables": {
        "owner": owner, "name": name, "number": number, "after": after}})
    done = subprocess.run(["gh", "api", "graphql", "--input", "-"],
                          input=payload, capture_output=True, text=True)
    result = json.loads(done.stdout or "{}")
    if done.returncode or result.get("errors"):
        sys.exit(f"graphql failed: {result.get('errors') or done.stderr}")
    return result["data"]


def short(text, width=70):
    text = " ".join(text.split())
    return text if len(text) <= width else text[:width] + "…"


def main():
    number = int(sys.argv[1])
    owner, name = (sys.argv[2] if len(sys.argv) > 2 else "HYGON-AI/TurboPhysAI").split("/")

    data, threads, after = None, [], None
    while True:
        data = fetch(owner, name, number, after)
        page = data["repository"]["pullRequest"]["reviewThreads"]
        threads += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    pr = data["repository"]["pullRequest"]
    login = data["viewer"]["login"]

    print(f"head {pr['headRefOid'][:8]} | mergeable {pr['mergeable']} | {len(threads)} threads")
    for review in pr["reviews"]["nodes"]:
        if review["author"]["login"] == login:
            print(f"you have an UNSUBMITTED pending review: {review['url']}")

    for i, t in enumerate(threads, 1):
        comments = t["comments"]["nodes"]
        first, last = comments[0], comments[-1]
        state = "resolved" if t["isResolved"] else "open"
        if t["isOutdated"]:
            state += ",outdated"
        line = t["line"] or t["originalLine"]
        print(f"\n[{i}] {state} | {t['path']}:{line} | thread {t['id']}")
        print(f"    {first['author']['login']}: {short(first['body'])}")
        if len(comments) == 1:
            print("    (no reply)")
        else:
            print(f"    last ({len(comments) - 1} replies) {last['author']['login']}: {short(last['body'])}")
        print(f"    {first['url']}")


if __name__ == "__main__":
    main()
