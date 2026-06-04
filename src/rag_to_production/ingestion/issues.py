import json
from collections.abc import Iterator
from pathlib import Path

from rag_to_production.domain.models import Document


def load_issues(issues_path: Path) -> Iterator[Document]:
    if not issues_path.exists():
        raise FileNotFoundError(
            f"Issues file missing at {issues_path}. "
            "It is committed as curated data (see ADR 003); restore it from the repository."
        )
    with issues_path.open(encoding="utf-8") as lines:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            thread = json.loads(line)
            # step 1 projects only `text`; the raw per-thread fields (number,
            # url, state, labels, dates, comments) stay in the file as
            # provenance for step 5, unused here.
            yield Document(id=f"issue-{thread['number']}", text=thread["text"], source="issues")
