"""Domain vocabulary per letter type, used to augment classifier training.

Template letters alone teach the classifier the wording of a few layouts.
Lexicon documents mix typical domain phrases with neutral letter phrases,
so the classifier learns the vocabulary of a domain instead of one layout.
"""

from __future__ import annotations

import random

from letterlens.domain import LetterType

LEXICON: dict[LetterType, list[str]] = {
    LetterType.TAX: [
        "Finanzamt", "Steuernummer", "Steueridentifikationsnummer", "Einkommensteuer",
        "Lohnsteuer", "Umsatzsteuer", "Kirchensteuer", "Solidaritätszuschlag",
        "Steuerbescheid", "Steuererklärung", "Veranlagung", "Vorauszahlung zur Einkommensteuer",
        "Abgabenordnung", "ELSTER", "Erhebungsstelle", "Finanzkasse", "Säumniszuschlag nach § 240 AO",
        "Verspätungszuschlag", "Einspruch beim Finanzamt", "Festsetzung der Steuer",
        "Erstattung Einkommensteuer", "Nachzahlung Steuer", "Kalenderjahr", "Werbungskosten",
        "Grundsteuer", "Kfz-Steuer", "Hauptzollamt", "Steuerpflichtige",
    ],
    LetterType.BENEFITS: [
        "Jobcenter", "Bürgergeld", "Grundsicherungsgeld", "Grundsicherung für Arbeitsuchende", "Arbeitslosengeld", "Agentur für Arbeit", "Familienkasse",
        "Kindergeld", "Kinderzuschlag", "Wohngeld", "Bedarfsgemeinschaft", "BG-Nummer",
        "Leistungen zur Sicherung des Lebensunterhalts", "Sozialgesetzbuch", "SGB II", "SGB I",
        "Weiterbewilligungsantrag", "Bewilligungszeitraum", "Regelbedarf", "Kosten der Unterkunft",
