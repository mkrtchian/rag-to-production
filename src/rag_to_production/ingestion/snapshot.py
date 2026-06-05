from pathlib import Path

import httpx

from rag_to_production.domain.models import ProseSource, SourceCheckout

_RAW_BASE = "https://raw.githubusercontent.com"
_API_BASE = "https://api.github.com"


def fetch_snapshot(snapshot_dir: Path, source: ProseSource) -> None:
    target = snapshot_dir / "docs"
    if target.exists() and any(target.iterdir()):
        return
    for blob_path in _wanted_blobs(source.repo, source.ref, (source.path,)):
        _download_blob(source.repo, source.ref, blob_path, target / blob_path)


def fetch_source_snapshot(snapshot_dir: Path, checkout: SourceCheckout) -> None:
    target = snapshot_dir / "source"
    if target.exists() and any(target.iterdir()):
        return
    for blob_path in _wanted_blobs(checkout.repo, checkout.ref, checkout.paths):
        if not is_extractable_source(blob_path):
            continue
        _download_blob(checkout.repo, checkout.ref, blob_path, target / blob_path)


def _wanted_blobs(repo: str, ref: str, paths: tuple[str, ...]) -> list[str]:
    url = f"{_API_BASE}/repos/{repo}/git/trees/{ref}?recursive=1"
    response = httpx.get(url, follow_redirects=True, timeout=60.0)
    response.raise_for_status()
    entries = response.json()["tree"]
    return [
        str(entry["path"])
        for entry in entries
        if entry["type"] == "blob" and is_wanted_path(str(entry["path"]), paths)
    ]


def is_wanted_path(blob_path: str, paths: tuple[str, ...]) -> bool:
    return any(blob_path == prefix or blob_path.startswith(f"{prefix}/") for prefix in paths)


def is_extractable_source(blob_path: str) -> bool:
    if not blob_path.endswith(".py"):
        return False
    segments = blob_path.split("/")
    return "tests" not in segments and "test" not in segments


def _download_blob(repo: str, ref: str, blob_path: str, destination: Path) -> None:
    url = f"{_RAW_BASE}/{repo}/{ref}/{blob_path}"
    response = httpx.get(url, follow_redirects=True, timeout=60.0)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
