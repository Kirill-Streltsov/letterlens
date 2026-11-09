"""The committed client fixtures must still match the API response models."""

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from letterlens.api import schemas as S

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
MODELS = {
    "create_letter": S.CreateLetterResponse,
    "letter_view": S.LetterView,
    "letter_list": list[S.LetterListItem],
    "me": S.MeResponse,
    "languages": list[S.LanguageInfo],
    "question_refused": S.QuestionResponse,
    "question_answered": S.QuestionResponse,
    "counselling_services": list[S.CounsellingService],
    "share": S.ShareInfo,
    "messages": list[S.MessageOut],
    "error": S.ErrorBody,
}


@pytest.mark.parametrize("name", sorted(MODELS))
def test_fixture_matches_model(name: str) -> None:
    path = FIXTURES / f"{name}.json"
    if not path.exists():
        pytest.skip("run scripts/export_fixtures.py")
    TypeAdapter(MODELS[name]).validate_python(json.loads(path.read_text(encoding="utf-8")))
