import CryptoKit
import Foundation

// MARK: - PKCE (RFC 7636)

public enum PKCE {
    public static func base64URL(_ data: Data) -> String {
        data.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }

    public static func makeVerifier() -> String {
        var bytes = [UInt8](repeating: 0, count: 48)
        for i in bytes.indices { bytes[i] = UInt8.random(in: 0...255) }
        return base64URL(Data(bytes))
    }

    public static func challenge(for verifier: String) -> String {
        base64URL(Data(SHA256.hash(data: Data(verifier.utf8))))
    }
}

// MARK: - OCR line ordering

/// One line recognized by Vision. Vision boxes are normalized with the origin at the bottom left.
public struct RecognizedLine: Sendable {
    public var text: String
    public var x: Double, y: Double, width: Double, height: Double
    public var confidence: Double
    public init(text: String, x: Double, y: Double, width: Double, height: Double, confidence: Double) {
        self.text = text; self.x = x; self.y = y; self.width = width; self.height = height; self.confidence = confidence
    }
}

public enum DocumentBuilder {
    /// Orders lines top-to-bottom (then left-to-right within a row) and numbers them per page.
    public static func build(pages: [[RecognizedLine]], engine: String = "apple-vision") -> LetterDocument {
        var lines: [OcrLine] = []
        for (pageIndex, page) in pages.enumerated() {
            let converted = page.map { line -> (RecognizedLine, BBox) in
                (line, BBox(x: line.x, y: max(0, 1 - line.y - line.height), w: line.width, h: line.height))
            }
            let ordered = converted.sorted { a, b in
                let rowTolerance = min(a.1.h, b.1.h) * 0.5
                if abs(a.1.y - b.1.y) > rowTolerance { return a.1.y < b.1.y }
