import pytest

from letterlens.safety.guardrail import (
    Verdict,
    check_question_rules,
    is_advisory_output,
)


@pytest.mark.parametrize(
    "question",
    [
        "Should I object to this decision?",
        "Do I have to pay this?",
        "Is this legal?",
        "Can my landlord really do this?",
        "Sollte ich Widerspruch einlegen?",
        "Muss ich das zahlen?",
        "Lohnt sich ein Einspruch?",
        "İtiraz etmeli miyim?",
        "هل يجب أن أعترض على هذا القرار؟",
        "Чи варто оскаржувати це рішення?",
        "Стоит ли мне обжаловать это решение?",
        "Write me an objection letter",
    ],
)
def test_legal_advice_requests_are_blocked(question: str) -> None:
    assert check_question_rules(question).verdict is Verdict.LEGAL_ADVICE


