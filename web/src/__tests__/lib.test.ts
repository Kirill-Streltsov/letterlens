import { toCsv } from "@/lib/csv";
import { daysUntil, money, relativeLabel, urgency } from "@/lib/format";
import { buildIcs } from "@/lib/ics";
import { documentFromText, toDocument } from "@/lib/ocr";

describe("calendar export", () => {
  it("builds an all-day event with a reminder", () => {
    const ics = buildIcs({ uid: "x", date: "2026-12-31", title: "Pay, please; now", description: "a\nb" }, new Date("2026-11-26T10:00:00Z"));
    expect(ics).toContain("DTSTART;VALUE=DATE:20261231");
    expect(ics).toContain("DTEND;VALUE=DATE:20270101");
    expect(ics).toContain("SUMMARY:Pay\\, please\\; now");
    expect(ics).toContain("TRIGGER:-P3D");
    expect(ics.split("\r\n").every((l) => l.length <= 75)).toBe(true);
  });
});

describe("formatting", () => {
  it("counts days and urgency", () => {
    const today = new Date(2026, 10, 26);
    expect(daysUntil("2026-11-29", today)).toBe(3);
    expect(urgency(3)).toBe("urgent");
    expect(urgency(-1)).toBe("past");
    expect(relativeLabel(1)).toBe("tomorrow");
  });

  it("formats euro amounts the German way", () => {
    expect(money("1523.5").replace(/\s/g, " ")).toBe("1.523,50 €");
  });
});

describe("OCR normalization", () => {
  it("numbers lines per page and drops empty lines", () => {
    const doc = toDocument(
      [
        { text: " Finanzamt  Bochum ", page: 1 },
        { text: "   ", page: 1 },
        { text: "Seite 2", page: 2 },
      ],
      "test",
    );
    expect(doc.lines.map((l) => [l.page, l.index, l.text])).toEqual([
      [1, 1, "Finanzamt Bochum"],
      [2, 1, "Seite 2"],
    ]);
  });

  it("splits pasted text into lines", () => {
    expect(documentFromText("a\n\nb").lines).toHaveLength(2);
  });
});

describe("CSV", () => {
  it("has a header and one row per entry", () => {
    expect(toCsv([{ month: "2026-11-01", letter_type: "tax", language: "tr", cases: 2, closed: 1 }])).toBe(
      "month,letter_type,language,cases,closed\n2026-11-01,tax,tr,2,1\n",
    );
  });
});
