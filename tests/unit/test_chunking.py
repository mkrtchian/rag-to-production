import tests.unit.test_chunking_given as given
import tests.unit.test_chunking_then as then
from rag_to_production.domain.chunking import chunk_document


def test_fixed_size_window_yields_expected_count_and_overlap():
    doc = given.a_document_of_length(250)
    policy = given.a_policy(chunk_size=100, overlap=20)

    chunks = chunk_document(doc, policy)

    # stride = 100 - 20 = 80: starts at 0, 80, 160, 240 -> 4 chunks
    then.chunk_count_is(chunks, 4)
    then.adjacent_chunks_overlap_by(chunks, 20)


def test_chunk_metadata_propagates_from_the_source_document():
    doc = given.a_document_of_length(250, source="issues")
    policy = given.a_policy(chunk_size=100, overlap=20)

    chunks = chunk_document(doc, policy)

    then.every_chunk_carries(chunks, document_id="doc-1", source="issues")
    then.chunk_ids_are_unique_and_derived_from(chunks, "doc-1")


def test_code_fence_is_split_mid_unit():
    doc = given.a_document_with_a_code_fence()
    policy = given.a_policy(chunk_size=15, overlap=3)

    chunks = chunk_document(doc, policy)

    then.the_code_fence_is_split_across_chunks(chunks)
