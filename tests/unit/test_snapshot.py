from rag_to_production.ingestion.snapshot import is_extractable_source, is_wanted_path


def test_matches_files_within_a_prefix_directory():
    assert is_wanted_path("src/oss/langgraph/install.mdx", ("src/oss/langgraph",))
    assert is_wanted_path(
        "src/oss/langgraph/errors/GRAPH_RECURSION_LIMIT.mdx", ("src/oss/langgraph",)
    )


def test_matches_an_exact_path():
    path = "src/oss/reference/langgraph-python.mdx"
    assert is_wanted_path(path, (path,))


def test_does_not_match_a_sibling_that_shares_the_prefix():
    assert not is_wanted_path("src/oss/langgraph-platform/index.mdx", ("src/oss/langgraph",))
    assert not is_wanted_path("src/oss/langgraphx.mdx", ("src/oss/langgraph",))
    assert not is_wanted_path("src/oss/langchain/install.mdx", ("src/oss/langgraph",))


def test_extracts_python_modules_outside_test_segments():
    assert is_extractable_source("libs/langgraph/langgraph/graph/state.py")


def test_ignores_non_python_files():
    assert not is_extractable_source("libs/langgraph/README.md")


def test_ignores_files_under_a_test_segment():
    assert not is_extractable_source("libs/langgraph/tests/test_graph.py")
    assert not is_extractable_source("libs/langgraph/test/helpers.py")
