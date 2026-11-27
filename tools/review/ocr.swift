// Usage: swiftc -O -o ocr tools/review/ocr.swift && ./ocr letter.pdf > letter.txt
// OCR a PDF (rendered pages) or an image with Apple Vision, like the iOS app.
// Usage: ocr <file> [firstPage] [lastPage]   -> prints "=== page N" and one text line per line.
import AppKit
import Foundation
import PDFKit
import Vision

func recognize(_ image: CGImage) -> [String] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["de-DE", "en-US"]
    request.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    try? handler.perform([request])
    let obs = (request.results ?? []).compactMap { o -> (CGRect, String)? in
        guard let t = o.topCandidates(1).first?.string else { return nil }
        return (o.boundingBox, t)
    }
    // Reading order: rows from top to bottom (Vision origin is bottom-left), then left to right.
    let sorted = obs.sorted { a, b in
        let dy = a.0.midY - b.0.midY
        if abs(dy) > min(a.0.height, b.0.height) * 0.5 { return dy > 0 }
        return a.0.minX < b.0.minX
    }
    var lines: [String] = []
    var current: (y: CGFloat, h: CGFloat, parts: [String])? = nil
    for (box, text) in sorted {
        if let c = current, abs(c.y - box.midY) <= min(c.h, box.height) * 0.5 {
            current!.parts.append(text)
        } else {
            if let c = current { lines.append(c.parts.joined(separator: "  ")) }
            current = (box.midY, box.height, [text])
        }
    }
    if let c = current { lines.append(c.parts.joined(separator: "  ")) }
    return lines
}

func render(_ page: PDFPage, scale: CGFloat = 3) -> CGImage? {
    let bounds = page.bounds(for: .mediaBox)
    let w = Int(bounds.width * scale), h = Int(bounds.height * scale)
    guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
    ctx.setFillColor(NSColor.white.cgColor)
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: ctx)
    return ctx.makeImage()
}

let args = CommandLine.arguments
let url = URL(fileURLWithPath: args[1])
if url.pathExtension.lowercased() == "pdf", let doc = PDFDocument(url: url) {
    let first = args.count > 2 ? Int(args[2])! : 1
    let last = args.count > 3 ? Int(args[3])! : doc.pageCount
    for i in (first - 1)..<min(last, doc.pageCount) {
        print("=== page \(i + 1)")
        if let page = doc.page(at: i), let img = render(page) { recognize(img).forEach { print($0) } }
    }
} else if let img = NSImage(contentsOf: url), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) {
    print("=== page 1")
    recognize(cg).forEach { print($0) }
}
