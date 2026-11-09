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

