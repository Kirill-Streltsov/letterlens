/**
 * On-device OCR in the browser. The letter image never leaves the device; only
 * the recognized text lines are sent to the API (data minimization, ADR-0005).
 *
 * Images: tesseract.js (German model). PDFs: the embedded text layer when the PDF
 * is digital, else each page is rendered and recognized.
 */

import type { LetterDocument } from "./api";

export interface RawLine {
  text: string;
  page: number;
  bbox?: { x: number; y: number; w: number; h: number };
  confidence?: number;
}

export type Progress = (message: string, fraction: number) => void;

/** Normalize OCR output into the API format: trimmed, non-empty, numbered per page. */
export function toDocument(lines: RawLine[], engine: string): LetterDocument {
  const counters = new Map<number, number>();
  const out = [];
  for (const line of lines) {
    const text = line.text.replace(/\s+/g, " ").trim();
    if (!text) continue;
    const index = (counters.get(line.page) ?? 0) + 1;
    counters.set(line.page, index);
    out.push({
      page: line.page,
      index,
      text: text.slice(0, 2000),
      bbox: line.bbox ?? null,
      confidence: line.confidence ?? null,
    });
  }
  return { lines: out.slice(0, 2000), ocr_engine: engine };
}

/** Plain text pasted by the user (for example from an e-mail or a digital PDF). */
export function documentFromText(text: string): LetterDocument {
  return toDocument(
    text.split(/\r?\n/).map((t) => ({ text: t, page: 1 })),
    "paste",
  );
}

async function recognizeCanvasOrImage(
  source: HTMLCanvasElement | File,
  page: number,
  width: number,
  height: number,
  progress: Progress,
): Promise<RawLine[]> {
  const { createWorker } = await import("tesseract.js");
  const worker = await createWorker("deu", 1, {
    logger: (m: { status: string; progress: number }) => progress(`Reading page ${page}: ${m.status}`, m.progress),
  });
  try {
    const { data } = await worker.recognize(source, {}, { blocks: true });
    const lines: RawLine[] = [];
    for (const block of data.blocks ?? []) {
      for (const paragraph of block.paragraphs) {
        for (const line of paragraph.lines) {
          lines.push({
            text: line.text,
            page,
            confidence: line.confidence / 100,
            bbox: width && height
              ? {
