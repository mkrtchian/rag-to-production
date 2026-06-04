"""Curate the committed LangGraph issue snapshot.

GitHub issues cannot be pinned by a repository SHA the way files can (they keep
evolving), so the snapshot is frozen as committed data (see ADR 003). This script
is the re-runnable curation command behind that frozen file: it re-fetches the
issue threads, applies the quality bar, and writes the jsonl. Re-running it later
produces a fresh snapshot at a new extraction date, not a bit-identical copy.

Requires the GitHub CLI (`gh`) authenticated. Run via `make fetch-issues`.
"""

import argparse
import datetime
import json
import subprocess
import time
from typing import Any, cast

DEFAULT_REPO = "langchain-ai/langgraph"
DEFAULT_OUTPUT = "data/langgraph-issues.jsonl"
MIN_COMMENT_CHARS = 80


def main() -> None:
    args = _parse_args()
    records = _curate(args.repo, args.min_comment_chars, args.extraction_date)
    records.sort(key=lambda record: record["number"])
    with open(args.output, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} issue threads to {args.output}")


def _curate(repo: str, min_comment_chars: int, extraction_date: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for issue in _gh_paginate(f"repos/{repo}/issues?state=all&per_page=100"):
        if "pull_request" in issue or _is_bot(issue.get("user")):
            continue
        if (issue.get("comments") or 0) == 0:
            continue
        comments = _gh_paginate(f"repos/{repo}/issues/{issue['number']}/comments?per_page=100")
        if not _has_human_answer(comments, min_comment_chars):
            continue
        records.append(_to_record(issue, comments, extraction_date))
    return records


def _has_human_answer(comments: list[Any], min_comment_chars: int) -> bool:
    return any(
        not _is_bot(comment.get("user")) and len(_text(comment.get("body"))) >= min_comment_chars
        for comment in comments
    )


def _to_record(issue: Any, raw_comments: list[Any], extraction_date: str) -> dict[str, Any]:
    title = _text(issue.get("title"))
    body = _text(issue.get("body"))
    comments = [
        {
            "author": _text(_field(comment.get("user"), "login")),
            "body": _text(comment.get("body")),
            "created_at": comment.get("created_at"),
        }
        for comment in raw_comments
    ]
    text = f"# {title}\n\n{body}" + "".join(f"\n\n{comment['body']}" for comment in comments)
    return {
        "number": issue["number"],
        "url": issue.get("html_url"),
        "title": title,
        "state": issue.get("state"),
        "labels": [_text(_field(label, "name")) for label in _list(issue.get("labels"))],
        "created_at": issue.get("created_at"),
        "closed_at": issue.get("closed_at"),
        "extraction_date": extraction_date,
        "body": body,
        "comments": comments,
        "text": text,
    }


def _gh_paginate(endpoint: str, retries: int = 2) -> list[Any]:
    for attempt in range(retries + 1):
        result = subprocess.run(
            ["gh", "api", "--paginate", endpoint], capture_output=True, text=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        if attempt < retries:
            time.sleep(5)
            continue
        raise RuntimeError(f"gh api failed for {endpoint}: {result.stderr[:300]}")
    return []


def _is_bot(user: Any) -> bool:
    return _field(user, "type") == "Bot"


def _field(obj: Any, key: str) -> Any:
    return cast("dict[str, Any]", obj).get(key) if isinstance(obj, dict) else None


def _list(obj: Any) -> list[Any]:
    return cast("list[Any]", obj) if isinstance(obj, list) else []


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Curate the committed LangGraph issue snapshot.")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--min-comment-chars", type=int, default=MIN_COMMENT_CHARS)
    parser.add_argument("--extraction-date", default=datetime.date.today().isoformat())
    return parser.parse_args()


if __name__ == "__main__":
    main()
