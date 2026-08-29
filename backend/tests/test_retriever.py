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


