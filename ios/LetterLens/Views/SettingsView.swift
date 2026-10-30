import LetterLensCore
import StoreKit
import SwiftUI

struct SettingsView: View {
    @Environment(AppModel.self) private var model
    @State private var name = ""
    @State private var language = "en"
    @State private var product: Product?
    @State private var confirmDelete = false

    var body: some View {
        Form {
            Section("Profile") {
                TextField("Name shown to counsellors (optional)", text: $name)
                Picker("Preferred language", selection: $language) {
                    ForEach(model.languages) { Text($0.nativeName).tag($0.code) }
                }
                Button("Save") {
                    Task {
                        do {
                            try await model.api.updateMe(displayName: name.isEmpty ? nil : name, preferredLanguage: language)
                            await model.loadProfile()
                        } catch { model.error = error.localizedDescription }
                    }
                }
            }

            Section {
                if model.me?.plan == "plus" {
                    Label("LetterLens Plus is active", systemImage: "checkmark.seal.fill").foregroundStyle(Theme.ok)
                } else if let product {
                    Button("Get Plus: unlimited letters, \(product.displayPrice) per month") {
                        Task {
                            do { try await model.store.purchase(product, userId: model.me?.id ?? "") } catch {
                                model.error = error.localizedDescription
                            }
                        }
                    }
                }
                Button("Restore purchases") { Task { try? await model.store.restore() } }
            } header: {
                Text("Plan")
            } footer: {
                if let me = model.me, let limit = me.lettersLimit {
                    Text("Free plan: \(me.lettersThisMonth) of \(limit) letters used this month.")
                }
            }

            Section("Your data") {
                Text("Letters are deleted automatically after 30 days. Photos never leave this iPhone.")
                    .font(.callout).foregroundStyle(Theme.inkSoft)
                Button("Delete my account and all letters", role: .destructive) { confirmDelete = true }
            }

            Section {
                Button("Sign out") { Task { await model.signOut() } }
            } footer: {
                Text("LetterLens gives general information, not legal advice.")
            }
        }
        .paperBackground()
        .navigationTitle("Settings")
        .confirmationDialog("Delete your account and all letters? This cannot be undone.", isPresented: $confirmDelete,
                            titleVisibility: .visible) {
            Button("Delete account", role: .destructive) {
                Task {
                    try? await model.api.deleteAccount()
                    await model.signOut()
                }
            }
        }
        .task {
            name = model.me?.displayName ?? ""
            language = model.me?.preferredLanguage ?? "en"
            product = try? await model.store.plusProduct()
        }
    }
}
