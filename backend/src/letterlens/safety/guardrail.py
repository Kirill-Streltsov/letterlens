"""Legal-advice guardrail.

LetterLens explains what a letter says. It does not assess the reader's
individual legal case (§ 2 (1) RDG). This module decides whether a user
question asks for such an assessment, and whether a generated text gives one.

Layer 1 is a multilingual rule set: fast, free, explainable.
Layer 2 is an LLM classifier (see letterlens.pipeline.qa). The policy blocks a
question when either layer flags it. Measured catch rate and false-positive
rate per layer are in evals/reports/guardrail.json.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class Verdict(StrEnum):
    ALLOW = "allow"
    LEGAL_ADVICE = "legal_advice"
    INJECTION = "prompt_injection"


@dataclass(frozen=True, slots=True)
class GuardResult:
    verdict: Verdict
    layer: str
    matched: str | None = None

    @property
    def blocked(self) -> bool:
        return self.verdict is not Verdict.ALLOW


# Questions that ask for a decision or a prognosis about the reader's own case.
_ADVICE_PATTERNS: dict[str, list[str]] = {
    "en": [
        r"\bshould i\b.*\b(object|appeal|contest|sign|pay|accept|refuse|complain|sue|ignore|respond|agree)",
        r"\b(do|must) i (really )?have to (pay|accept|move|leave|agree)",
        r"\b(is|was) (this|it|that) (legal|lawful|illegal|allowed|valid|correct|right)\b",
        r"\bcan (they|the \w+|my landlord|the office) (really )?(do|demand|ask|charge|evict|deport)",
        r"\b(my|our) chances\b|\bwill i win\b|\bwin (the|this|my) (case|appeal)",
        r"\b(is|would) (an? )?(objection|appeal|complaint|lawsuit) (worth|make sense|succeed)",
        r"\bwhat (would|should) (you|i) (do|write)\b.*\b(object|appeal|case|landlord|office)",
        r"\bwrite (me )?(an? )?(objection|appeal|widerspruch|einspruch)\b",
        r"\bare they (allowed|entitled)\b|\bam i (entitled|obliged|liable)\b",
        r"\bhow (do|can) i (avoid|get out of) (paying|the fine|deportation)",
    ],
    "de": [
        r"\bsoll(te)? ich\b.*\b(widerspruch|einspruch|klagen|zahlen|unterschreiben|zustimmen)",
        r"\bmuss ich (wirklich |das |den betrag )?(zahlen|zustimmen|ausziehen|bezahlen)",
        r"\b(ist|war) (das|dies|der bescheid|die kündigung) (rechtens|legal|zulässig|rechtmäßig|gültig)",
        r"\b(darf|dürfen|kann) (der vermieter|das amt|die behörde|das jobcenter|die|der) (das|mir|mich|einfach)",
        r"\blohnt sich (ein |der )?(widerspruch|einspruch|klage)",
        r"\b(meine|habe ich) (chancen|recht)\b|\bhabe ich anspruch\b",
        r"\bschreib(en sie| mir)? (einen |mir einen )?(widerspruch|einspruch)",
        r"\bwas würden sie (an meiner stelle )?tun\b",
    ],
    "tr": [
        r"itiraz etmeli miyim|itiraz etsem mi|ödemeli miyim|ödemek zorunda mıyım",
        r"imzalamalı mıyım|kabul etmeli miyim|dava açmalı mıyım",
        r"(bu|bunu) yasal mı|hakları var mı|haklı mıyım|kazanır mıyım|şansım",
        r"itiraz (dilekçesi|mektubu) yaz",
    ],
    "ar": [
        r"هل (يجب|ينبغي) (علي|عليّ) (أن )?(أعترض|أدفع|أوقع|أقبل|أرفع)",
        r"هل يجب أن (أعترض|أدفع|أوقع)",
        r"هل (هذا|ذلك) قانوني|هل يحق (لهم|له|للمالك)|هل لدي (فرصة|حق)",
        r"(اكتب|أكتب) (لي )?(اعتراض|طعن)",
        r"ما هي فرصي|هل سأربح",
    ],
    "uk": [
        r"чи (варто|треба|потрібно|слід) (мені )?(оскаржувати|оскаржити|платити|сплачувати|підписувати|погоджуватися)",
        r"чи (маю|повинен|повинна) я (платити|сплатити|підписати|погодитися)",
        r"чи (це|є це) законно|чи мають вони право|чи маю я право",
        r"(напиши|напишіть) (мені )?(заперечення|скаргу|оскарження)",
        r"які (мої )?шанси|чи виграю я",
    ],
    "ru": [
        r"(стоит|нужно|надо|следует) ли (мне )?(обжаловать|оспаривать|платить|подписывать|соглашаться)",
        r"(должен|должна|обязан|обязана) ли я (платить|подписать|соглашаться)",
        r"(это|это вообще) законно|имеют ли они право|имею ли я право",
        r"(напиши|напишите) (мне )?(возражение|жалобу)",
        r"какие (у меня )?шансы|выиграю ли я",
    ],
}

_INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)",
    r"ignoriere (alle )?(vorherigen|bisherigen) (anweisungen|regeln)",
    r"\byou are now (dan|a different|an? (ai|assistant|lawyer|unrestricted))|du bist jetzt (ein|eine)\b",
    r"system prompt|developer mode|jailbreak",
    r"reveal (your|the) (prompt|instructions)|zeige (deinen|den) prompt",
    r"</?(system|assistant|letter|document)>",
]

# Generated text that reads like an individual recommendation.
_ADVISORY_OUTPUT = [
    r"\byou should (definitely |probably )?(object|appeal|not pay|refuse|sue|sign|contest)",
    r"\bI (would )?(recommend|advise) (you )?(to )?(object|appeal|pay|refuse|sign|contest)",
    r"\byour (objection|appeal|case) (will|would|is likely to) (succeed|win|fail)",
    r"\b(this|the) (decision|letter|notice|demand) is (unlawful|illegal|invalid|wrong)\b",
    r"\bsie sollten (unbedingt |auf jeden fall )?(widerspruch|einspruch|klage|nicht zahlen)",
    r"\bder bescheid ist (rechtswidrig|falsch|unwirksam)",
    r"\bich (empfehle|rate) ihnen\b",
]


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns]


_ADVICE = {lang: _compile(p) for lang, p in _ADVICE_PATTERNS.items()}
_INJECTION = _compile(_INJECTION_PATTERNS)
_ADVISORY = _compile(_ADVISORY_OUTPUT)


