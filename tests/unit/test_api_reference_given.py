from pathlib import Path
from textwrap import dedent

from rag_to_production.domain.models import SourceCheckout
from rag_to_production.ingestion.api_reference import ModuleSource

STATE_MODULE = dedent('''
    class StateGraph(Generic[StateT]):
        """Build a graph whose nodes share typed state."""

        def add_node(self, name: str, action: Callable) -> "Self":
            """Register a node under name."""

        def _private(self) -> None:
            """Hidden helper, never rendered."""


    def add_messages(left: list, right: list = []) -> list:
        """Merge two message lists."""
''')

GRAPH_INIT = dedent("""
    from langgraph.graph.state import StateGraph

    __all__ = ["StateGraph"]
""")

TYPES_MODULE = dedent('''
    class Command:
        """A control-flow directive returned by a node."""

    class _Internal:
        """Should never be rendered."""

    __all__ = ["Command"]
''')

CONSTANTS_MODULE = dedent("""
    START = "__start__"
    END = "__end__"

    __all__ = ["START", "END"]
""")

CHECKPOINT_BASE_INIT = dedent('''
    from langgraph.checkpoint.memory import InMemorySaver


    class BaseCheckpointSaver:
        """Persist and load graph checkpoints."""

        def get(self, config: dict) -> dict:
            """Fetch the checkpoint for config."""


    def _build_default() -> None:
        """Internal, excluded by the non-underscore fallback."""
''')

CHECKPOINT_MEMORY_MODULE = dedent('''
    class InMemorySaver:
        """Keep checkpoints in memory."""
''')

OUTSIDE_IMPORT_INIT = dedent("""
    from langchain_core.runnables import Runnable

    __all__ = ["Runnable"]
""")

NOT_ALL_NON_INIT = dedent('''
    class Hidden:
        """Defined in a plain module that is not a public entry point."""
''')

OVERLOADED_MODULE = dedent('''
    from typing import overload


    class Updater:
        """Apply an update."""

        @overload
        def apply(self, value: int) -> int: ...
        @overload
        def apply(self, value: str) -> str: ...
        def apply(self, value):
            """Apply value and return it."""
            return value


    @overload
    def merge(left: int, right: int) -> int: ...
    @overload
    def merge(left: str, right: str) -> str: ...
    def merge(left, right):
        """Merge left and right."""
        return left + right

    __all__ = ["Updater", "merge"]
''')


def a_module(source: str, *, is_package: bool) -> ModuleSource:
    return ModuleSource(source=source, is_package=is_package)


def a_state_graph_package() -> dict[str, ModuleSource]:
    return {
        "langgraph.graph": a_module(GRAPH_INIT, is_package=True),
        "langgraph.graph.state": a_module(STATE_MODULE, is_package=False),
    }


def a_function_only_package() -> dict[str, ModuleSource]:
    init = 'from langgraph.graph.state import add_messages\n\n__all__ = ["add_messages"]\n'
    return {
        "langgraph.graph": a_module(init, is_package=True),
        "langgraph.graph.state": a_module(STATE_MODULE, is_package=False),
    }


def a_checkpoint_package_without_all() -> dict[str, ModuleSource]:
    return {
        "langgraph.checkpoint.base": a_module(CHECKPOINT_BASE_INIT, is_package=True),
        "langgraph.checkpoint.memory": a_module(CHECKPOINT_MEMORY_MODULE, is_package=True),
    }


def a_plain_module_not_an_entry_point() -> dict[str, ModuleSource]:
    return {"langgraph.internal.hidden": a_module(NOT_ALL_NON_INIT, is_package=False)}


def write_snapshot_tree(snapshot_dir: Path) -> SourceCheckout:
    package_root = snapshot_dir / "source" / "libs" / "langgraph" / "langgraph"
    _write(package_root / "graph" / "__init__.py", GRAPH_INIT)
    _write(package_root / "graph" / "state.py", STATE_MODULE)
    return SourceCheckout(
        repo="langchain-ai/langgraph",
        ref="deadbeef",
        paths=("libs/langgraph/langgraph",),
    )


def _write(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
