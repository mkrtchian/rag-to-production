from dataclasses import dataclass, field
from pathlib import Path

from rag_to_production.domain.chunking import ChunkingPolicy
from rag_to_production.domain.models import ProseSource


@dataclass(frozen=True)
class Settings:
    embedder_model: str = "BAAI/bge-small-en-v1.5"
    llm_model: str = "gemini-3.1-flash-lite"
    chunking: ChunkingPolicy = field(default=ChunkingPolicy(chunk_size=1000, overlap=200))
    k: int = 5
    chroma_dir: Path = field(default=Path("chroma"))
    snapshot_dir: Path = field(default=Path("snapshot"))
    # LangGraph prose lives in the langchain-ai/docs monorepo. Pinned to a commit
    # SHA so the build is reproducible. Only the LangGraph subtree is fetched, not
    # the whole monorepo (LangChain prose under src/oss/langchain is left out: the
    # LangChain/LangGraph conflation stays a named limit, not something fabricated
    # by dumping LangChain docs). The API reference layer (ADR 003) is generated
    # from the langchain-ai/langgraph source docstrings, not static prose, so its
    # ingestion is a heavier later step: the current build covers prose + issues.
    docs: ProseSource = field(
        default=ProseSource(
            repo="langchain-ai/docs",
            ref="5a3a8abf24f00d9e04f49cd94b1fc8fa02044530",
            path="src/oss/langgraph",
        )
    )
    issues_path: Path = field(default=Path("data/langgraph-issues.jsonl"))
