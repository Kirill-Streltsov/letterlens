import Foundation

public struct APIError: Error, Equatable, LocalizedError, Sendable {
    public let status: Int
    public let code: String
    public let message: String
    public var errorDescription: String? { message }
}

/// Supplies authentication headers (Bearer token or the local dev header).
public protocol AuthHeaderProvider: Sendable {
    func headers() async throws -> [String: String]
}

public final class APIClient: Sendable {
    public let baseURL: URL
    private let auth: AuthHeaderProvider
    private let session: URLSession

    public init(baseURL: URL, auth: AuthHeaderProvider, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.auth = auth
        self.session = session
    }

    // MARK: Coding

    public static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let raw = try decoder.singleValueContainer().decode(String.self)
            if let date = parseISODate(raw) { return date }
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "bad date \(raw)"))
        }
        return decoder
    }()

    public static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }()

    /// Parses ISO 8601 with 0 to 6 fractional digits (Python emits microseconds).
    public static func parseISODate(_ raw: String) -> Date? {
        var value = raw
        if let dot = value.firstIndex(of: "."), let zone = value[dot...].firstIndex(where: { $0 == "Z" || $0 == "+" || $0 == "-" }) {
            let fraction = value[value.index(after: dot)..<zone].prefix(3)
            value = String(value[..<dot]) + "." + fraction.padding(toLength: 3, withPad: "0", startingAt: 0) + String(value[zone...])
        }
        let withFraction = ISO8601DateFormatter()
        withFraction.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let plain = ISO8601DateFormatter()
        plain.formatOptions = [.withInternetDateTime]
        return withFraction.date(from: value) ?? plain.date(from: value)
    }

    // MARK: Transport

    private struct Empty: Codable {}

    private func send<T: Decodable>(_ method: String, _ path: String, body: (any Encodable)? = nil,
                                    headers extra: [String: String] = [:]) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL) else { throw URLError(.badURL) }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 30
        for (key, value) in try await auth.headers().merging(extra, uniquingKeysWith: { $1 }) {
            request.setValue(value, forHTTPHeaderField: key)
        }
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try Self.encoder.encode(body)
        }
        let (data, response) = try await session.data(for: request)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(status) else {
            let body = try? Self.decoder.decode(ErrorBody.self, from: data)
            throw APIError(status: status, code: body?.code ?? "http_\(status)", message: body?.message ?? "Request failed (\(status))")
        }
        if status == 204 || data.isEmpty, let empty = Empty() as? T { return empty }
        return try Self.decoder.decode(T.self, from: data)
    }

