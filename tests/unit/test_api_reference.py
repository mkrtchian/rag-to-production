from pathlib import Path

import pytest

import tests.unit.test_api_reference_given as given
import tests.unit.test_api_reference_then as then
from rag_to_production.ingestion.api_reference import (
    load_api_reference,
    public_symbols,
    render_symbol,
)


def test_public_function_renders_signature_and_docstring():
    modules = given.a_function_only_package()

    symbols = public_symbols(modules)

    then.the_only_qualname_is(symbols, "langgraph.graph.add_messages")
    then.the_symbol_text_contains(
        symbols,
        "langgraph.graph.add_messages",
        "def add_messages(left: list, right: list=[]) -> list:",
        "Merge two message lists.",
    )


def test_public_class_renders_public_methods_and_excludes_private():
    modules = given.a_state_graph_package()

    symbols = public_symbols(modules)

    then.the_symbol_text_contains(
        symbols,
        "class StateGraph(Generic[StateT]):",
        "Build a graph whose nodes share typed state.",
        "def add_node(self, name: str, action: Callable) -> 'Self':",
        "Register a node under name.",
    )
    then.the_symbol_text_excludes(symbols, "_private", "Hidden helper")


def test_all_is_honored_so_an_absent_name_yields_no_symbol():
    modules = given.a_state_graph_package()

    symbols = public_symbols(modules)

    # state.py defines add_messages too, but graph/__init__ only exports StateGraph
    then.the_only_qualname_is(symbols, "langgraph.graph.StateGraph")


def test_re_export_resolves_with_the_public_entry_point_id():
    modules = given.a_state_graph_package()

    symbols = public_symbols(modules)

    # id is the exporting path, text comes from state.py
    then.the_only_qualname_is(symbols, "langgraph.graph.StateGraph")
    then.the_symbol_text_contains(symbols, "class StateGraph(Generic[StateT]):")


def test_public_non_init_module_with_all_exposes_local_names():
    modules = {"langgraph.types": given.a_module(given.TYPES_MODULE, is_package=False)}

    symbols = public_symbols(modules)

    then.the_only_qualname_is(symbols, "langgraph.types.Command")
    then.the_symbol_text_contains(symbols, "A control-flow directive returned by a node.")


def test_init_without_all_falls_back_to_non_underscore_surface():
    modules = given.a_checkpoint_package_without_all()

    symbols = public_symbols(modules)

    # BaseCheckpointSaver defined locally, InMemorySaver re-exported, _build_default dropped
    then.the_qualnames_are(
        symbols,
        "langgraph.checkpoint.base.BaseCheckpointSaver",
        "langgraph.checkpoint.base.InMemorySaver",
        "langgraph.checkpoint.memory.InMemorySaver",
    )


def test_plain_module_without_all_is_not_an_entry_point():
    modules = given.a_plain_module_not_an_entry_point()

    symbols = public_symbols(modules)

    then.no_symbols(symbols)


def test_name_imported_from_outside_the_snapshot_is_dropped():
    modules = {"langgraph.x": given.a_module(given.OUTSIDE_IMPORT_INIT, is_package=True)}

    symbols = public_symbols(modules)

    then.no_symbols(symbols)


def test_bare_constants_yield_no_symbol():
    modules = {"langgraph.constants": given.a_module(given.CONSTANTS_MODULE, is_package=False)}

    symbols = public_symbols(modules)

    then.no_symbols(symbols)


def test_render_symbol_returns_none_for_a_non_def_name():
    assert render_symbol("langgraph.constants", "START", given.CONSTANTS_MODULE) is None


def test_render_symbol_preserves_annotations_and_defaults():
    rendered = render_symbol("langgraph.graph.state", "add_messages", given.STATE_MODULE)

    assert rendered is not None
    assert "def add_messages(left: list, right: list=[]) -> list:" in rendered


def test_load_api_reference_walks_a_tmp_tree(tmp_path: Path):
    checkout = given.write_snapshot_tree(tmp_path)

    documents = list(load_api_reference(tmp_path, checkout))

    then.the_document_ids_are(documents, "langgraph.graph.StateGraph")
    then.every_document_is_api_ref(documents)
    then.the_document_text_contains(
        documents,
        "langgraph.graph.StateGraph",
        "class StateGraph(Generic[StateT]):",
        "Build a graph whose nodes share typed state.",
    )


def test_missing_snapshot_raises_a_clear_fetch_first_error(tmp_path: Path):
    checkout = given.SourceCheckout(repo="r", ref="x", paths=("libs/langgraph/langgraph",))

    with pytest.raises(FileNotFoundError, match="Fetch"):
        list(load_api_reference(tmp_path, checkout))
