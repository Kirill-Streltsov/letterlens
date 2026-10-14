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

