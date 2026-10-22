import Foundation
import LetterLensCore
import Observation

/// Build-time configuration from Info.plist (values come from Config/*.xcconfig).
struct AppConfig {
    let apiBaseURL: URL
    let authDomain: String
    let clientId: String
    let devUser: String

    static let current: AppConfig = {
        let info = Bundle.main.infoDictionary ?? [:]
        func value(_ key: String) -> String { (info[key] as? String)?.trimmingCharacters(in: .whitespaces) ?? "" }
        return AppConfig(
            apiBaseURL: URL(string: value("LLApiBaseURL")) ?? URL(string: "http://localhost:8000")!,
            authDomain: value("LLAuthDomain"),
            clientId: value("LLClientId"),
            devUser: value("LLDevUser")
        )
    }()

    var usesDevAuth: Bool { !devUser.isEmpty }
}

@MainActor
@Observable
final class AppModel {
    enum Phase { case loading, signedOut, signedIn }

    var phase: Phase = .loading
    var me: Me?
    var languages: [LanguageInfo] = []
    var error: String?

    let config = AppConfig.current
    let auth: AuthService
    let api: APIClient
    let store = StoreService()

    init() {
        auth = AuthService(config: AppConfig.current)
        api = APIClient(baseURL: AppConfig.current.apiBaseURL, auth: auth)
    }

    func start() async {
        store.onVerifiedTransaction = { [weak self] jws in
            guard let self else { return }
            Task { await self.submitTransaction(jws) }
        }
        store.listenForTransactions()
        if await auth.isSignedIn() {
            await loadProfile()
        } else {
            phase = .signedOut
        }
    }

    func signIn() async {
        do {
            try await auth.signIn()
            await loadProfile()
        } catch AuthError.cancelled {
            return
        } catch {
            self.error = error.localizedDescription
        }
    }

    func signOut() async {
        await auth.signOut()
        me = nil
        phase = .signedOut
    }

