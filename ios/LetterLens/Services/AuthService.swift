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

