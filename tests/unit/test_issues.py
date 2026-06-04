import json
from pathlib import Path

from rag_to_production.ingestion.issues import load_issues

_KEY = "sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0U1v2"


def test_load_issues_scrubs_a_leaked_key_before_it_reaches_a_document(tmp_path: Path):
    issues_path = tmp_path / "issues.jsonl"
    thread = {"number": 7, "text": f'config: os.environ["OPENAI_API_KEY"] = "{_KEY}"'}
    issues_path.write_text(json.dumps(thread) + "\n", encoding="utf-8")

    documents = list(load_issues(issues_path))

    assert len(documents) == 1
    assert _KEY not in documents[0].text
    assert "[REDACTED-SECRET]" in documents[0].text
