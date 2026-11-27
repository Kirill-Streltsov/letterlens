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
    # The app's buttons are in English in every language, so the button name stays English.
    "en": (
        "I can explain what the letter says, but I cannot assess your personal case or tell "
        "you what to decide. A counselling service can do this, often for free. Use "
        '"Talk to a counsellor" to share this letter with one.'
    ),
    "de": (
        "Ich kann erklären, was im Brief steht. Ich kann aber Ihren persönlichen Fall nicht "
        "rechtlich prüfen und Ihnen keine Entscheidung empfehlen. Eine Beratungsstelle kann das, "
        'oft kostenlos. Mit "Talk to a counsellor" können Sie den Brief mit einer Beratungsstelle teilen.'
    ),
    "tr": (
        "Mektupta ne yazdığını açıklayabilirim, ancak kişisel durumunuzu hukuki olarak "
        "değerlendiremem ve size ne karar vermeniz gerektiğini söyleyemem. Bir danışma "
        'merkezi bunu yapabilir, çoğu zaman ücretsiz. Mektubu paylaşmak için "Talk to a counsellor" '
        "bölümünü kullanın."
    ),
    "ar": (
        "يمكنني شرح ما يقوله الخطاب، لكن لا يمكنني تقييم حالتك الشخصية قانونياً أو إخبارك "
        "بما يجب أن تقرره. يمكن لمركز استشارات القيام بذلك، وغالباً مجاناً. استخدم "
        '"Talk to a counsellor" لمشاركة هذا الخطاب.'
    ),
    "uk": (
        "Я можу пояснити, що написано в листі, але не можу юридично оцінити вашу особисту "
        "ситуацію чи порадити, яке рішення ухвалити. Консультаційна служба може це зробити, "
        "часто безкоштовно. Скористайтеся «Talk to a counsellor», щоб поділитися листом."
    ),
    "ru": (
        "Я могу объяснить, что написано в письме, но не могу юридически оценить вашу личную "
        "ситуацию или посоветовать, какое решение принять. Консультационная служба может это "
        "сделать, часто бесплатно. Используйте «Talk to a counsellor», чтобы поделиться письмом."
    ),
}

COUNSELLING_HINT: dict[str, str] = {
    # Tenant associations (Mietervereine) charge a membership fee, so they are not called free.
    "en": "Free help: migration counselling (MBE, JMD) and social counselling services can look at "
    "your case. Tenant associations help their members with rent questions.",
    "de": "Kostenlose Hilfe: Migrationsberatung (MBE, JMD) und Sozialberatung können Ihren Fall "
    "ansehen. Mietervereine helfen ihren Mitgliedern bei Fragen zur Miete.",
    "tr": "Ücretsiz yardım: göçmen danışma hizmetleri (MBE, JMD) ve sosyal danışma merkezleri "
    "durumunuza bakabilir. Kiracı dernekleri, kira konularında üyelerine yardım eder.",
    "ar": "مساعدة مجانية: يمكن لخدمات استشارة المهاجرين (MBE وJMD) ومراكز الاستشارة الاجتماعية "
    "النظر في حالتك. تساعد جمعيات المستأجرين أعضاءها في مسائل الإيجار.",
    "uk": "Безкоштовна допомога: міграційні консультації (MBE, JMD) і соціальні консультації можуть "
    "розглянути вашу ситуацію. Спілки орендарів допомагають своїм членам із питаннями оренди.",
    "ru": "Бесплатная помощь: миграционные консультации (MBE, JMD) и социальные консультации могут "
    "рассмотреть вашу ситуацию. Союзы арендаторов помогают своим членам в вопросах аренды.",
}

DISCLAIMER: dict[str, str] = {
    "en": "General information, not legal advice. Always check dates and amounts in the original.",
    "de": "Allgemeine Information, keine Rechtsberatung. Prüfen Sie Daten und Beträge im Original.",
    "tr": "Genel bilgidir, hukuki danışmanlık değildir. Tarihleri ve tutarları her zaman "
    "orijinal mektupta kontrol edin.",
    "ar": "معلومات عامة وليست استشارة قانونية. تحقق دائماً من التواريخ والمبالغ في الخطاب الأصلي.",
    "uk": "Загальна інформація, не юридична консультація. Завжди перевіряйте дати й суми в оригіналі.",
    "ru": "Общая информация, не юридическая консультация. Всегда проверяйте даты и суммы в оригинале.",
}


def localized(table: dict[str, str], code: str) -> str:
    return table.get(code) or table["en"]
