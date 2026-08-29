from letterlens.domain import LetterType
from letterlens.llm.providers.fake import hash_embedding
from letterlens.rag.corpus import load_corpus
from letterlens.rag.retriever import EmbeddingIndex, HybridRetriever


def test_corpus_is_valid() -> None:
    entries = load_corpus()
    assert len(entries) >= 20
    for e in entries:
        assert e.source_url.startswith("https://")
        assert e.letter_types
        assert 40 < len(e.text.split()) < 220, e.id


def test_type_filter() -> None:
    r = HybridRetriever()
    for p in r.search("Mieterhöhung Zustimmung Mietspiegel", LetterType.LANDLORD):
        entry = next(e for e in r.entries if e.id == p.doc_id)
        assert LetterType.LANDLORD in entry.letter_types


def test_relevant_passage_ranks_first() -> None:
    r = HybridRetriever()
    cases = {
        ("Mahnung Mietrückstand bitte gleichen Sie den Rückstand aus", LetterType.LANDLORD): "rent-arrears",
        ("Einladung zum Gespräch Termin Jobcenter", LetterType.BENEFITS): "jobcenter-appointment",
        ("Betriebskostenabrechnung Nachzahlung", LetterType.LANDLORD): "utility-statement",
        ("Anhörung wir beabsichtigen Ihren Antrag abzulehnen", LetterType.IMMIGRATION): "hearing-letter",
    }
    for (query, letter_type), expected in cases.items():
        assert r.search(query, letter_type)[0].doc_id == expected


def test_passage_ids_are_sequential_citation_ids() -> None:
    passages = HybridRetriever().search("Einspruch Steuerbescheid", LetterType.TAX, k=3)
    assert [p.id for p in passages] == ["c1", "c2", "c3"][: len(passages)]


def test_dense_scores_fuse_with_bm25() -> None:
    entries = load_corpus()
    index = EmbeddingIndex(model="test", vectors={e.id: hash_embedding(e.searchable()) for e in entries})
    r = HybridRetriever(index=index, embedder=lambda texts: [hash_embedding(t) for t in texts])
    assert r.search("Einspruch Steuerbescheid Finanzamt", LetterType.TAX)[0].doc_id == "tax-objection"


def test_failing_embedder_falls_back_to_bm25() -> None:
    entries = load_corpus()
    index = EmbeddingIndex(model="test", vectors={e.id: [0.0] for e in entries})

    def broken(texts: list[str]) -> list[list[float]]:
        raise RuntimeError("provider down")

    r = HybridRetriever(index=index, embedder=broken)
    assert r.search("Einspruch Steuerbescheid", LetterType.TAX)
