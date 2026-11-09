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

