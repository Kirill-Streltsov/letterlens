"""Synthetic letters for training, evaluation and demos."""

from letterlens.domain import LetterDocument, OcrLine
from letterlens.synthetic.generator import SyntheticLetter, generate, generate_corpus


def to_document(letter: SyntheticLetter) -> LetterDocument:
    """Convert a synthetic letter to the OCR format that clients send. Empty lines are dropped."""
    lines = [
        OcrLine(page=1, index=i, text=text, confidence=0.99)
        for i, text in enumerate((t for t in letter.lines if t.strip()), start=1)
    ]
    return LetterDocument(lines=lines, ocr_engine="synthetic")


__all__ = ["SyntheticLetter", "generate", "generate_corpus", "to_document"]
