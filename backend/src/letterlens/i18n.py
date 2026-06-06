"""Output languages and the fixed safety texts in each language.

A language is ENABLED only when its faithfulness score in the latest
evaluation is at or above the threshold (evals/thresholds.yaml). The
evaluation job updates ``status`` in languages.yaml; this module reads it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

import yaml

from letterlens.config import get_settings


class LanguageStatus(StrEnum):
    ENABLED = "enabled"
    EXPERIMENTAL = "experimental"  # visible with a warning; below threshold or not yet measured
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class Language:
    code: str
    name: str
    native_name: str
    rtl: bool
    status: LanguageStatus
    faithfulness: float | None


_DEFAULT_FILE = Path(__file__).with_name("languages.yaml")


@lru_cache(maxsize=1)
def languages() -> dict[str, Language]:
    path = Path(get_settings().languages_file or _DEFAULT_FILE)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        code: Language(
            code=code,
            name=item["name"],
            native_name=item["native_name"],
            rtl=bool(item.get("rtl", False)),
            status=LanguageStatus(item["status"]),
            faithfulness=item.get("faithfulness"),
        )
        for code, item in raw["languages"].items()
    }


def is_available(code: str) -> bool:
    lang = languages().get(code)
    return lang is not None and lang.status is not LanguageStatus.DISABLED


REFUSAL: dict[str, str] = {
    "en": (
        "I can explain what the letter says, but I cannot assess your personal case or tell "
        "you what to decide. A counselling service can do this for free. Tap "
        "\"Talk to a counsellor\" to share this letter with one."
    ),
    "de": (
        "Ich kann erklären, was im Brief steht. Ich kann aber Ihren persönlichen Fall nicht "
        "rechtlich prüfen und Ihnen keine Entscheidung empfehlen. Eine Beratungsstelle hilft "
        "Ihnen kostenlos. Tippen Sie auf \"Mit Beratung sprechen\"."
    ),
    "tr": (
        "Mektupta ne yazdığını açıklayabilirim, ancak kişisel durumunuzu hukuki olarak "
        "değerlendiremem ve size ne karar vermeniz gerektiğini söyleyemem. Bir danışma "
        "merkezi bunu ücretsiz yapabilir. Mektubu paylaşmak için \"Danışmanla konuş\" "
        "düğmesine dokunun."
    ),
    "ar": (
        "يمكنني شرح ما يقوله الخطاب، لكن لا يمكنني تقييم حالتك الشخصية قانونياً أو إخبارك "
        "بما يجب أن تقرره. يمكن لمركز استشارات مساعدتك مجاناً. اضغط على \"تحدث مع مستشار\" "
        "لمشاركة هذا الخطاب."
    ),
    "uk": (
        "Я можу пояснити, що написано в листі, але не можу юридично оцінити вашу особисту "
        "ситуацію чи порадити, яке рішення ухвалити. Консультаційна служба допоможе "
        "безкоштовно. Натисніть «Поговорити з консультантом», щоб поділитися листом."
    ),
    "ru": (
        "Я могу объяснить, что написано в письме, но не могу юридически оценить вашу личную "
        "ситуацию или посоветовать, какое решение принять. Консультационная служба поможет "
        "бесплатно. Нажмите «Поговорить с консультантом», чтобы поделиться письмом."
    ),
}

