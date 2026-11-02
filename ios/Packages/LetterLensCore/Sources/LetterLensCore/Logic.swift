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
                return a.1.x < b.1.x
            }
            var index = 0
            for (line, box) in ordered {
                let text = line.text.split(whereSeparator: \.isWhitespace).joined(separator: " ")
                guard !text.isEmpty else { continue }
                index += 1
                lines.append(OcrLine(page: pageIndex + 1, index: index, text: String(text.prefix(2000)),
                                     bbox: box, confidence: line.confidence))
            }
        }
        return LetterDocument(lines: Array(lines.prefix(2000)), ocrEngine: engine)
    }

    public static func fromText(_ text: String) -> LetterDocument {
        let lines = text.split(separator: "\n", omittingEmptySubsequences: false)
            .map { $0.split(whereSeparator: \.isWhitespace).joined(separator: " ") }
            .filter { !$0.isEmpty }
            .enumerated()
            .map { OcrLine(page: 1, index: $0.offset + 1, text: $0.element) }
        return LetterDocument(lines: lines, ocrEngine: "paste")
    }
}

// MARK: - Deadlines

public enum Urgency: Equatable, Sendable { case past, urgent, soon, later }

public enum Deadlines {
    private static var utc: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "UTC")!
        return calendar
    }

    public static func date(fromISO iso: String) -> Date? {
        let parts = iso.prefix(10).split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3 else { return nil }
        return utc.date(from: DateComponents(year: parts[0], month: parts[1], day: parts[2], hour: 12))
    }

    public static func daysUntil(_ iso: String, today: Date = Date(), calendar: Calendar = .current) -> Int? {
        guard let target = date(fromISO: iso) else { return nil }
        let local = calendar.dateComponents([.year, .month, .day], from: today)
        guard let start = utc.date(from: DateComponents(year: local.year, month: local.month, day: local.day, hour: 12)) else {
            return nil
        }
        return utc.dateComponents([.day], from: start, to: target).day
    }

    public static func urgency(days: Int) -> Urgency {
        switch days {
        case ..<0: .past
        case 0...3: .urgent
        case 4...14: .soon
        default: .later
        }
    }

    public static func relativeLabel(days: Int) -> String {
        switch days {
        case ..<(-1): "\(-days) days ago"
        case -1: "yesterday"
        case 0: "today"
        case 1: "tomorrow"
        default: "in \(days) days"
        }
    }

