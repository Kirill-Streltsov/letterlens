import Foundation
import Testing
@testable import LetterLensCore

private let fixtures = URL(fileURLWithPath: #filePath)
    .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    .appendingPathComponent("contracts/fixtures")

private func load<T: Decodable>(_ name: String, as type: T.Type) throws -> T {
    let data = try Data(contentsOf: fixtures.appendingPathComponent("\(name).json"))
    return try APIClient.decoder.decode(T.self, from: data)
}

@Suite("Contract: real API responses decode")
struct ContractTests {
    @Test func letterView() throws {
        let letter = try load("letter_view", as: LetterView.self)
        #expect(letter.status == .ready)
        #expect(letter.facts?.deadlines.isEmpty == false)
        #expect(letter.explanation?.summary.isEmpty == false)
        #expect(letter.lines.first?.id == "p1-l1")
    }

    @Test func otherResponses() throws {
        _ = try load("letter_list", as: [LetterListItem].self)
        _ = try load("me", as: Me.self)
        _ = try load("languages", as: [LanguageInfo].self)
        _ = try load("create_letter", as: CreateLetterResponse.self)
        _ = try load("counselling_services", as: [CounsellingService].self)
        _ = try load("share", as: ShareInfo.self)
        _ = try load("messages", as: [Message].self)
        let refused = try load("question_refused", as: QuestionResponse.self)
        #expect(refused.refused && refused.handoverSuggested)
        let error = try load("error", as: ErrorBody.self)
        #expect(error.code == "not_found")
    }

    @Test func requestBodiesUseSnakeCase() throws {
        let doc = LetterDocument(lines: [OcrLine(page: 1, index: 1, text: "x")], ocrEngine: "test")
        let json = String(decoding: try APIClient.encoder.encode(doc), as: UTF8.self)
        #expect(json.contains("\"ocr_engine\""))
    }
}

@Suite struct DateParsingTests {
    @Test(arguments: ["2026-11-26T15:16:09.809331Z", "2026-11-26T15:16:09Z", "2026-11-26T15:16:09.8Z"])
    func parsesPythonTimestamps(raw: String) {
        #expect(APIClient.parseISODate(raw) != nil)
    }
}

@Suite struct PKCETests {
    @Test func rfc7636Example() {
        #expect(PKCE.challenge(for: "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
    }

    @Test func verifierIsURLSafe() {
        let verifier = PKCE.makeVerifier()
        #expect(verifier.count >= 43)
        #expect(verifier.allSatisfy { $0.isLetter || $0.isNumber || $0 == "-" || $0 == "_" })
    }
}

@Suite struct DocumentBuilderTests {
    @Test func ordersTopToBottomAndFlipsY() {
        let lines = [
            RecognizedLine(text: "second", x: 0.1, y: 0.70, width: 0.5, height: 0.02, confidence: 0.9),
            RecognizedLine(text: "first", x: 0.1, y: 0.90, width: 0.5, height: 0.02, confidence: 0.9),
            RecognizedLine(text: "  ", x: 0.1, y: 0.50, width: 0.5, height: 0.02, confidence: 0.9),
            RecognizedLine(text: "right", x: 0.6, y: 0.701, width: 0.2, height: 0.02, confidence: 0.9),
        ]
        let doc = DocumentBuilder.build(pages: [lines, [lines[0]]])
        #expect(doc.lines.map(\.text) == ["first", "second", "right", "second"])
        #expect(doc.lines.map(\.id) == ["p1-l1", "p1-l2", "p1-l3", "p2-l1"])
        #expect(abs((doc.lines[0].bbox?.y ?? 0) - 0.08) < 0.0001)
    }

    @Test func pastedText() {
        #expect(DocumentBuilder.fromText("a\n\n  b  c ").lines.map(\.text) == ["a", "b c"])
    }
}

