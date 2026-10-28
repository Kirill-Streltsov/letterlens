import LetterLensCore
import SwiftUI

struct SignInView: View {
    @Environment(AppModel.self) private var model
    @State private var busy = false

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            EnvelopeArt()
            VStack(spacing: 12) {
                Text("Understand the letter.\nKeep the deadline.")
                    .font(Theme.title(32)).multilineTextAlignment(.center).foregroundStyle(Theme.ink)
                Text("Scan an official letter. LetterLens explains it in your language and finds the deadlines. Text recognition runs on your phone.")
                    .multilineTextAlignment(.center).foregroundStyle(Theme.inkSoft)
            }
            Spacer()
            Button {
                busy = true
                Task { await model.signIn(); busy = false }
            } label: {
                Text(model.config.usesDevAuth ? "Continue (local demo)" : "Sign in or create an account")
                    .font(.headline).frame(maxWidth: .infinity).padding(.vertical, 6)
            }
            .buttonStyle(.borderedProminent).disabled(busy)
            Text("General information, not legal advice.").font(.footnote).foregroundStyle(Theme.inkSoft)
        }
        .padding(28)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .paperBackground()
    }
}

