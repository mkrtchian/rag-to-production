from rag_to_production.domain.models import RetrievedChunk


def top_result_is_document(results: list[RetrievedChunk], document_id: str) -> None:
    assert results, "expected at least one retrieved chunk"
    assert results[0].chunk.document_id == document_id


def no_result_is_document(results: list[RetrievedChunk], document_id: str) -> None:
    assert all(result.chunk.document_id != document_id for result in results)


def scores_are_similarities_in_descending_order(results: list[RetrievedChunk]) -> None:
    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)
    assert all(-1.0 <= score <= 1.0 for score in scores)
