# ADR-0005: On-device OCR instead of Amazon Textract

Status: accepted · Date: 2026-11-16

## Context

The reference plan uses Amazon Textract as the source of truth for text. Textract
is paid after a short trial, and it needs the letter image on a server.

## Decision

1. The iOS app recognizes text on the device with Apple Vision (`VNRecognizeTextRequest`, German, accurate level) after the VisionKit document scanner.
2. The web app recognizes text in the browser with tesseract.js (German model). For digital PDFs it reads the text layer.
3. The clients send only text lines with page, index, normalized bounding box and confidence.
4. Images go to S3 only if the reader agrees, for a counsellor to see the original.

## Consequences

- The server never needs the image. This is the strongest data-minimization measure in the product.
- OCR quality depends on the device. The reader sees the recognized text before sending, and the original letter stays on screen next to the explanation.
- Amounts and dates are verified against the same text the reader sees, so OCR errors become "please check", not wrong facts.

## Alternatives

- **Textract**: better on tables; paid; image leaves the device. Possible later as an optional server-side OCR adapter.
- **Multimodal model on the image**: the model would see the full image with all personal data. Rejected.
