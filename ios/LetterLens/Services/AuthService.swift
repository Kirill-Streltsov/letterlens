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

    func signIn() async throws {
        if config.usesDevAuth {
            keychain.write("dev", Data(config.devUser.utf8))
            return
        }
        guard !config.authDomain.isEmpty, !config.clientId.isEmpty else { throw AuthError.misconfigured }
        let verifier = PKCE.makeVerifier()
        var components = URLComponents(string: "https://\(config.authDomain)/oauth2/authorize")!
        components.queryItems = [
            .init(name: "response_type", value: "code"),
            .init(name: "client_id", value: config.clientId),
            .init(name: "redirect_uri", value: redirectURI),
            .init(name: "scope", value: "openid email profile"),
            .init(name: "code_challenge_method", value: "S256"),
            .init(name: "code_challenge", value: PKCE.challenge(for: verifier)),
        ]
        let callback = try await WebAuthenticator.authenticate(url: components.url!, scheme: "letterlens")
        guard let code = URLComponents(url: callback, resolvingAgainstBaseURL: false)?
            .queryItems?.first(where: { $0.name == "code" })?.value else { throw AuthError.cancelled }
        _ = try await exchange([
            "grant_type": "authorization_code", "code": code,
            "code_verifier": verifier, "redirect_uri": redirectURI,
        ])
    }

    func signOut() {
        tokens = nil
        keychain.delete("tokens")
        keychain.delete("dev")
    }

    private func exchange(_ params: [String: String]) async throws -> StoredTokens {
        var request = URLRequest(url: URL(string: "https://\(config.authDomain)/oauth2/token")!)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        var form = URLComponents()
        form.queryItems = (params.merging(["client_id": config.clientId]) { $1 }).map { URLQueryItem(name: $0.key, value: $0.value) }
        request.httpBody = form.percentEncodedQuery?.data(using: .utf8)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw AuthError.tokenExchangeFailed }
        struct TokenResponse: Decodable { let access_token: String; let refresh_token: String?; let expires_in: Double }
        let body = try JSONDecoder().decode(TokenResponse.self, from: data)
        let stored = StoredTokens(
            accessToken: body.access_token,
            refreshToken: body.refresh_token ?? params["refresh_token"],
            expiresAt: Date().addingTimeInterval(body.expires_in)
        )
        tokens = stored
        keychain.write("tokens", try JSONEncoder().encode(stored))
        return stored
    }
}

/// Bridges ASWebAuthenticationSession to async/await.
@MainActor
final class WebAuthenticator: NSObject, ASWebAuthenticationPresentationContextProviding {
    private static var current: WebAuthenticator?
    private var session: ASWebAuthenticationSession?

    static func authenticate(url: URL, scheme: String) async throws -> URL {
        let authenticator = WebAuthenticator()
        current = authenticator
        defer { current = nil }
        return try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(url: url, callbackURLScheme: scheme) { callback, error in
                if let callback { continuation.resume(returning: callback) } else {
                    continuation.resume(throwing: (error as? ASWebAuthenticationSessionError)?.code == .canceledLogin
                        ? AuthError.cancelled : (error ?? AuthError.cancelled))
                }
            }
            session.presentationContextProvider = authenticator
            session.prefersEphemeralWebBrowserSession = true
            authenticator.session = session
            session.start()
        }
    }

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.connectedScenes.compactMap { ($0 as? UIWindowScene)?.keyWindow }.first ?? ASPresentationAnchor()
    }
}

