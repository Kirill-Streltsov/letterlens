import AuthenticationServices
import Foundation
import LetterLensCore
import Security
import UIKit

enum AuthError: LocalizedError {
    case cancelled, misconfigured, tokenExchangeFailed
    var errorDescription: String? {
        switch self {
        case .cancelled: "Sign-in was cancelled."
        case .misconfigured: "Sign-in is not configured in this build."
        case .tokenExchangeFailed: "Sign-in failed. Please try again."
        }
    }
}

struct StoredTokens: Codable {
    var accessToken: String
    var refreshToken: String?
    var expiresAt: Date
}

/// Cognito hosted UI with OAuth 2.0 authorization code + PKCE. Tokens are kept in the Keychain
/// (this device only). Debug builds against a local API use the dev header instead.
actor AuthService: AuthHeaderProvider {
    private let config: AppConfig
    private let keychain = Keychain(service: "app.letterlens.auth")
    private var tokens: StoredTokens?
    private let redirectURI = "letterlens://auth/callback"

    init(config: AppConfig) {
        self.config = config
    }

    func isSignedIn() -> Bool {
        if config.usesDevAuth { return keychain.read("dev") != nil }
        tokens = tokens ?? keychain.read("tokens").flatMap { try? JSONDecoder().decode(StoredTokens.self, from: $0) }
        return tokens != nil
    }

    func headers() async throws -> [String: String] {
        if config.usesDevAuth { return ["X-Dev-User": config.devUser] }
        guard var current = tokens else { return [:] }
        if current.expiresAt.timeIntervalSinceNow < 60, let refresh = current.refreshToken {
            current = try await exchange(["grant_type": "refresh_token", "refresh_token": refresh])
        }
        return ["Authorization": "Bearer \(current.accessToken)"]
    }

