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

struct LettersView: View {
    @Environment(AppModel.self) private var model
    @State private var letters: [LetterListItem]?
    @State private var showNew = false

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                if let me = model.me, let limit = me.lettersLimit {
                    Text("\(max(limit - me.lettersThisMonth, 0)) of \(limit) free letters left this month")
                        .font(.footnote).foregroundStyle(Theme.inkSoft).frame(maxWidth: .infinity, alignment: .leading)
                }
                if letters == nil {
                    ProgressView().padding(.top, 60)
                } else if letters?.isEmpty == true {
                    VStack(spacing: 16) {
                        EnvelopeArt()
                        Text("No letters yet").font(Theme.title(22))
                        Text("Scan your first letter. It is deleted automatically after 30 days.")
                            .multilineTextAlignment(.center).foregroundStyle(Theme.inkSoft)
                        Button("Scan a letter") { showNew = true }.buttonStyle(.borderedProminent)
                    }
                    .card().padding(.top, 24)
                }
                ForEach(letters ?? []) { letter in
                    NavigationLink(value: letter.id) { LetterRow(letter: letter) }.buttonStyle(.plain)
                }
            }
            .padding()
        }
        .paperBackground()
        .navigationTitle("My letters")
        .navigationDestination(for: String.self) { LetterDetailView(letterId: $0) }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button { showNew = true } label: { Label("New letter", systemImage: "doc.viewfinder") }
            }
        }
        .sheet(isPresented: $showNew, onDismiss: { Task { await load() } }) {
            NavigationStack { NewLetterView() }
        }
        .refreshable { await load() }
        .task { await load() }
    }

    private func load() async {
        do { letters = try await model.api.letters() } catch { model.error = error.localizedDescription; letters = letters ?? [] }
    }
}

