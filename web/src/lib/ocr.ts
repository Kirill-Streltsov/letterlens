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
                  x: line.bbox.x0 / width,
                  y: line.bbox.y0 / height,
                  w: (line.bbox.x1 - line.bbox.x0) / width,
                  h: (line.bbox.y1 - line.bbox.y0) / height,
                }
              : undefined,
          });
        }
      }
    }
    return lines;
  } finally {
    await worker.terminate();
  }
}

async function imageSize(file: File): Promise<[number, number]> {
  const bitmap = await createImageBitmap(file);
  const size: [number, number] = [bitmap.width, bitmap.height];
  bitmap.close();
  return size;
}

async function readPdf(file: File, progress: Progress): Promise<RawLine[]> {
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
  const pdf = await pdfjs.getDocument({ data: await file.arrayBuffer() }).promise;
  const lines: RawLine[] = [];
  for (let p = 1; p <= Math.min(pdf.numPages, 6); p++) {
    const page = await pdf.getPage(p);
    const content = await page.getTextContent();
    const rows = new Map<number, string[]>();
    for (const item of content.items) {
      if (!("str" in item) || !item.str.trim()) continue;
      const y = Math.round(item.transform[5]);
      rows.set(y, [...(rows.get(y) ?? []), item.str]);
    }
    if (rows.size > 3) {
      [...rows.entries()].sort((a, b) => b[0] - a[0]).forEach(([, parts]) => lines.push({ text: parts.join(" "), page: p }));
      continue;
    }
    // Scanned PDF: render and recognize.
    const viewport = page.getViewport({ scale: 2 });
    const canvas = document.createElement("canvas");
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    await page.render({ canvas, viewport }).promise;
    lines.push(...(await recognizeCanvasOrImage(canvas, p, canvas.width, canvas.height, progress)));
  }
  return lines;
}

