import { base64Url, challengeFor } from "@/lib/auth";
import { toCsv } from "@/lib/csv";
import { daysUntil, money, relativeLabel, urgency } from "@/lib/format";
import { buildIcs } from "@/lib/ics";
import { documentFromText, toDocument } from "@/lib/ocr";

describe("PKCE", () => {
  it("encodes base64url without padding", () => {
    expect(base64Url(new Uint8Array([251, 255, 0]))).toBe("-_8A");
  });

  it("matches the RFC 7636 appendix B example", async () => {
    const verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";
    expect(await challengeFor(verifier)).toBe("E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");
  });
});

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

