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

public struct LetterDocument: Codable, Hashable, Sendable {
    public var lines: [OcrLine]
    public var ocrEngine: String
    public init(lines: [OcrLine], ocrEngine: String) { self.lines = lines; self.ocrEngine = ocrEngine }
}

public enum LetterStatus: String, Codable, Sendable { case received, processing, ready, failed }
public enum FactStatus: String, Codable, Sendable { case verified, needsCheck = "needs_check" }

public struct Classification: Codable, Hashable, Sendable {
    public var letterType: String
    public var confidence: Double
    public var modelVersion: String
    public var abstained: Bool
}

public struct ExtractedText: Codable, Hashable, Sendable {
    public var value: String?
    public var lineIds: [String]
}

public struct ReferenceNumber: Codable, Hashable, Sendable {
    public var label: String
    public var value: String
    public var lineIds: [String]
}

public struct VerifiedDeadline: Codable, Hashable, Sendable, Identifiable {
    public var id: String
    public var dueDate: String?
    public var status: FactStatus
    public var isEstimate: Bool
    public var description: String
    public var sourceText: String?
    public var lineIds: [String]
    public var rule: String?
    public var note: String?
}

public struct VerifiedAmount: Codable, Hashable, Sendable, Identifiable {
    public var id: String
    public var value: String
    public var currency: String
    public var direction: String
    public var status: FactStatus
    public var description: String
    public var lineIds: [String]
    public var note: String?
}

public struct RequiredAction: Codable, Hashable, Sendable {
    public var description: String
    public var lineIds: [String]
}

public struct VerifiedFacts: Codable, Hashable, Sendable {
    public var sender: ExtractedText
    public var subject: ExtractedText
    public var letterDate: String?
    public var letterDateStatus: FactStatus
    public var referenceNumbers: [ReferenceNumber]
    public var deadlines: [VerifiedDeadline]
    public var amounts: [VerifiedAmount]
    public var requiredActions: [RequiredAction]
    public var groundingRate: Double
}

public struct SummarySentence: Codable, Hashable, Sendable {
    public var text: String
    public var lineIds: [String]
}

public struct NextStep: Codable, Hashable, Sendable {
    public var text: String
    public var citationIds: [String]
}

public struct Citation: Codable, Hashable, Sendable, Identifiable {
    public var id: String
    public var title: String
    public var sourceUrl: String
    public var sourceName: String
    public var checkedOn: String
}

public struct Explanation: Codable, Hashable, Sendable {
    public var language: String
    public var headline: String
    public var letterKind: String
    public var summary: [SummarySentence]
    public var nextSteps: [NextStep]
    public var deadlineLabels: [String: String]
    public var amountLabels: [String: String]
    public var citations: [Citation]
    public var counsellingHint: String
    public var disclaimer: String
    public var faithfulness: Double?
    public var model: String
}

public struct ShareInfo: Codable, Hashable, Sendable, Identifiable {
    public var id: String
    public var tenantId: String
    public var tenantName: String
    public var caseStatus: String
    public var expiresAt: Date
    public var revoked: Bool
}

