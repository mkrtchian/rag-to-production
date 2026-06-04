from pathlib import Path

import tests.integration.test_retrieval_given as given
import tests.integration.test_retrieval_then as then
from rag_to_production.pipeline import index_corpus


def test_query_returns_the_chunk_whose_text_answers_it(tmp_path: Path):
    corpus = given.a_corpus_with_a_distinctive_chunk()
    embedder = given.a_real_embedder()
    store = given.a_temp_dir_store(tmp_path)
    index_corpus(corpus, embedder, store, given.the_naive_chunking_policy())

    query_embedding = embedder.embed(["how do I add a conditional edge in LangGraph?"])[0]
    results = store.search(query_embedding, k=3)

    then.top_result_is_document(results, document_id="doc-edges")
    then.scores_are_similarities_in_descending_order(results)
