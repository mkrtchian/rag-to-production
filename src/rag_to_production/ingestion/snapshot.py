import io
import tarfile
from pathlib import Path

import httpx

_REPOS = {
    "docs": "langchain-ai/docs",
    "langgraph": "langchain-ai/langgraph",
}


def fetch_snapshot(snapshot_dir: Path, docs_ref: str, langgraph_ref: str) -> None:
    refs = {"docs": docs_ref, "langgraph": langgraph_ref}
    for name, repo in _REPOS.items():
        target = snapshot_dir / name
        if target.exists():
            continue
        _download_tarball(repo, refs[name], target)


def _download_tarball(repo: str, ref: str, target: Path) -> None:
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    response = httpx.get(url, follow_redirects=True, timeout=60.0)
    response.raise_for_status()
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as archive:
        _extract_stripping_root(archive, target)


def _extract_stripping_root(archive: tarfile.TarFile, target: Path) -> None:
    for member in archive.getmembers():
        relative = member.name.split("/", 1)
        if len(relative) < 2 or not relative[1]:
            continue
        member.name = relative[1]
        archive.extract(member, target, filter="data")
