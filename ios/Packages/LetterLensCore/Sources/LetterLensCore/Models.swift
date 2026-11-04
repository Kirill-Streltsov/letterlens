import Foundation

// API models. They mirror contracts/openapi.json; the contract tests decode the real
// responses in contracts/fixtures/ so a server change cannot silently break the app.
// JSON keys are snake_case; the decoder converts them (APIClient.decoder).

public struct BBox: Codable, Hashable, Sendable {
    public var x: Double, y: Double, w: Double, h: Double
    public init(x: Double, y: Double, w: Double, h: Double) { self.x = x; self.y = y; self.w = w; self.h = h }
}

public struct OcrLine: Codable, Hashable, Sendable, Identifiable {
    public var page: Int
    public var index: Int
    public var text: String
    public var bbox: BBox?
    public var confidence: Double?
    public var id: String { "p\(page)-l\(index)" }

    public init(page: Int, index: Int, text: String, bbox: BBox? = nil, confidence: Double? = nil) {
        self.page = page; self.index = index; self.text = text; self.bbox = bbox; self.confidence = confidence
    }
}

