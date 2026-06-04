from dataclasses import dataclass, field
from pathlib import Path

from rag_to_production.domain.chunking import ChunkingPolicy


@dataclass(frozen=True)
class Settings:
    embedder_model: str = "BAAI/bge-small-en-v1.5"
    llm_model: str = "gemini-3.1-flash-lite"
    chunking: ChunkingPolicy = field(default=ChunkingPolicy(chunk_size=1000, overlap=200))
    k: int = 5
    chroma_dir: Path = field(default=Path("chroma"))
    snapshot_dir: Path = field(default=Path("snapshot"))
    # pinned ref placeholders (pin to commit SHAs or tags when the snapshot
    # fetch lands in step 3, so the build stays reproducible)
    docs_ref: str = "PINNED_DOCS_REF"
    langgraph_ref: str = "PINNED_LANGGRAPH_REF"
    issues_path: Path = field(default=Path("data/langgraph-issues.jsonl"))
