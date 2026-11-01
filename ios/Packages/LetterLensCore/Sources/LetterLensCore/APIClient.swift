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

