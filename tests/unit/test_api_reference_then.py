from rag_to_production.domain.models import Document
from rag_to_production.ingestion.api_reference import PublicSymbol


def the_only_qualname_is(symbols: list[PublicSymbol], qualname: str) -> None:
    assert [symbol.qualname for symbol in symbols] == [qualname]


def no_symbols(symbols: list[PublicSymbol]) -> None:
    assert symbols == []


def the_symbol_text_contains(symbols: list[PublicSymbol], *fragments: str) -> None:
    assert len(symbols) == 1
    text = symbols[0].text
    for fragment in fragments:
        assert fragment in text, f"{fragment!r} not in:\n{text}"


def the_symbol_text_excludes(symbols: list[PublicSymbol], *fragments: str) -> None:
    assert len(symbols) == 1
    text = symbols[0].text
    for fragment in fragments:
        assert fragment not in text, f"{fragment!r} unexpectedly in:\n{text}"


def the_qualnames_are(symbols: list[PublicSymbol], *qualnames: str) -> None:
    assert sorted(symbol.qualname for symbol in symbols) == sorted(qualnames)


def the_document_ids_are(documents: list[Document], *ids: str) -> None:
    assert sorted(document.id for document in documents) == sorted(ids)


def every_document_is_api_ref(documents: list[Document]) -> None:
    assert documents
    for document in documents:
        assert document.source == "api_ref"


def the_document_text_contains(
    documents: list[Document], document_id: str, *fragments: str
) -> None:
    document = next(d for d in documents if d.id == document_id)
    for fragment in fragments:
        assert fragment in document.text, f"{fragment!r} not in:\n{document.text}"
