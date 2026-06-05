from dataclasses import dataclass, field
from pathlib import Path

from rag_to_production.domain.chunking import ChunkingPolicy
from rag_to_production.domain.models import ProseSource, SourceCheckout


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
    # by dumping LangChain docs). The build covers three layers: prose, API
    # reference, and issues.
    docs: ProseSource = field(
        default=ProseSource(
            repo="langchain-ai/docs",
            ref="5a3a8abf24f00d9e04f49cd94b1fc8fa02044530",
            path="src/oss/langgraph",
        )
    )
    api_ref: SourceCheckout = field(
        default=SourceCheckout(
            repo="langchain-ai/langgraph",
            ref="43682f0830f312822f18206dfa18c599becbff38",  # confirmed downloadable 2026-06-05
            paths=(
                "libs/langgraph/langgraph",
                "libs/prebuilt/langgraph",
                "libs/checkpoint/langgraph",
            ),
        )
    )
    issues_path: Path = field(default=Path("data/langgraph-issues.jsonl"))
