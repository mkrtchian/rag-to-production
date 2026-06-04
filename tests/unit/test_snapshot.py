from rag_to_production.ingestion.snapshot import is_wanted_path


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
