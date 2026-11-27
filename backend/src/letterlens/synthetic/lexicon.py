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
        "Mitwirkungspflicht", "Meldeaufforderung", "Eingliederungsvereinbarung",
        "Kooperationsplan", "Leistungsminderung", "Erstattungsbescheid", "Elterngeld",
        "Sozialamt", "Grundsicherung", "Arbeitsvermittlung",
    ],
    LetterType.HEALTH_INSURANCE: [
        "Krankenkasse", "Krankenversicherung", "Versichertennummer", "Pflegeversicherung",
        "Beitrag zur Krankenversicherung", "Beitragsrückstand", "freiwillige Versicherung",
        "Familienversicherung", "Gesundheitskarte", "Medizinischer Dienst", "Kostenübernahme",
        "Krankengeld", "Zuzahlung", "Leistungsabteilung", "AOK", "Techniker Krankenkasse",
        "BARMER", "DAK", "IKK", "Hilfsmittel", "Rehabilitation", "Arbeitsunfähigkeit",
        "Pflegegrad", "Befreiung von Zuzahlungen", "Mitgliedschaft", "Beitragseinzug",
    ],
    LetterType.IMMIGRATION: [
        "Ausländerbehörde", "Ausländeramt", "Aufenthaltserlaubnis", "Aufenthaltstitel",
        "Niederlassungserlaubnis", "Aufenthaltsgesetz", "AufenthG", "Fiktionsbescheinigung",
        "Visum", "Duldung", "Aufenthaltsgestattung", "Reisepass", "biometrisches Foto",
        "Einbürgerung", "Staatsangehörigkeit", "Integrationskurs", "Blaue Karte EU",
        "Bundesamt für Migration und Flüchtlinge", "BAMF", "Asylverfahren", "Ausreisepflicht",
        "Zuwanderung", "Verlängerung des Aufenthalts", "Ausweisung", "elektronischer Aufenthaltstitel",
    ],
    LetterType.LANDLORD: [
        "Vermieter", "Mieter", "Mietvertrag", "Miete", "Nettokaltmiete", "Warmmiete",
        "Betriebskosten", "Nebenkostenabrechnung", "Betriebskostenabrechnung", "Vorauszahlung",
        "Mietrückstand", "Mieterhöhung", "Mietspiegel", "ortsübliche Vergleichsmiete",
        "Kaution", "Kündigung des Mietverhältnisses", "Wohnung", "Hausverwaltung",
        "Modernisierung", "Schönheitsreparaturen", "Heizkosten", "Hausordnung",
        "Wohnungsübergabe", "Mietkonto", "Wohnungsgenossenschaft", "Mieternummer",
    ],
    LetterType.OTHER: [
        "Rundfunkbeitrag", "Beitragsservice", "Inkasso", "Forderung", "Mandantin",
        "Bußgeldbescheid", "Bußgeldstelle", "Ordnungswidrigkeit", "Geldbuße", "Verwarnungsgeld",
        "Anhörungsbogen", "Fahrverbot", "Fahreignungsregister", "Geschwindigkeitsüberschreitung", "OWiG",
        "Fahrzeughalter", "Mahnbescheid", "Vollstreckungsbescheid", "Mahngericht", "Amtsgericht",
        "Antragsgegner", "Antragsteller", "Hauptforderung", "Gerichtsvollzieher", "Zwangsvollstreckung",
        "Stadtwerke", "Abschlag", "Strom", "Gas", "Mobilfunkvertrag", "Rechnung",
        "Vertragsverlängerung", "Kundenservice", "Bank", "Kontoauszug", "Fitnessstudio",
        "Versandhandel", "Bestellung", "Lieferung", "Gutschein", "Zeitschriftenabo",
        "Bibliothek", "Schule", "Elternabend", "Kita-Beitrag", "Sportverein", "Arztpraxis Termin",
        "Telekommunikation", "Energieversorger", "Zählerstand",
    ],
}  # fmt: skip

NEUTRAL = [
    "Sehr geehrte Damen und Herren,", "Mit freundlichen Grüßen", "Bitte beachten Sie",
    "Datum", "Seite 1 von 2", "Anlage", "Bei Rückfragen erreichen Sie uns", "Ihr Zeichen",
    "Bitte bewahren Sie dieses Schreiben auf", "Im Auftrag", "Öffnungszeiten",
    "Bitte geben Sie bei Zahlungen immer an", "Bankverbindung", "Telefon", "E-Mail",
    "wir möchten Sie informieren", "vielen Dank für Ihr Schreiben", "bis zum",
]  # fmt: skip


def lexicon_documents(per_type: int, seed: int) -> list[tuple[str, str]]:
    rnd = random.Random(seed)
    docs: list[tuple[str, str]] = []
    for letter_type, phrases in LEXICON.items():
        for _ in range(per_type):
            k = rnd.randint(4, 10)
            parts = rnd.sample(phrases, k) + rnd.sample(NEUTRAL, rnd.randint(3, 8))
            rnd.shuffle(parts)
            docs.append(("\n".join(parts), letter_type.value))
    return docs
