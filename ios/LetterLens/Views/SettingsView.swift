import LetterLensCore
import StoreKit
import SwiftUI

struct SettingsView: View {
    @Environment(AppModel.self) private var model
    @State private var name = ""
    @State private var language = "en"
    @State private var product: Product?
    @State private var confirmDelete = false
    @State private var saved = 0
    @State private var toast: Toast?

    private var dirty: Bool {
        name != (model.me?.displayName ?? "") || language != (model.me?.preferredLanguage ?? "en")
    }

    var body: some View {
        Form {
            Section {
                ProfileHeader(name: model.me?.displayName, plan: model.me?.plan ?? "free")
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets(top: 4, leading: 0, bottom: 8, trailing: 0))
            }

            Section("Profile") {
                TextField("Name shown to counsellors (optional)", text: $name)
                Picker("Preferred language", selection: $language) {
                    ForEach(model.languages) { Text($0.nativeName).tag($0.code) }
                }
                Button {
                    Task {
                        do {
                            try await model.api.updateMe(displayName: name.isEmpty ? nil : name, preferredLanguage: language)
                            await model.loadProfile()
                            saved += 1
                            toast = Toast(text: "Profile saved")
                        } catch { model.error = error.localizedDescription }
                    }
                } label: {
                    Label("Save", systemImage: "checkmark.circle.fill")
                        .symbolEffect(.bounce, value: saved)
                }
                .disabled(!dirty)
            }
            .listRowBackground(Theme.card)

            Section {
                if model.me?.plan == "plus" {
                    Label("LetterLens Plus is active", systemImage: "checkmark.seal.fill").foregroundStyle(Theme.ok)
                } else {
                    if let me = model.me, let limit = me.lettersLimit {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("Free plan").fontWeight(.semibold)
                                Spacer()
                                Text("\(me.lettersThisMonth) of \(limit) letters used").font(.footnote).foregroundStyle(Theme.inkSoft)
                            }
                            ProgressBar(value: Double(me.lettersThisMonth) / Double(max(limit, 1)))
                        }
                        .padding(.vertical, 4)
                    }
                    if let product {
                        Button {
                            Task {
                                do { try await model.store.purchase(product, userId: model.me?.id ?? "") } catch {
                                    model.error = error.localizedDescription
                                }
                            }
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: "sparkles").font(.title3).foregroundStyle(Color(UIColor(hex: 0x1B2540)))
                                    .frame(width: 40, height: 40).background(Theme.highlighter, in: RoundedRectangle(cornerRadius: 10))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Get Plus").font(.headline).foregroundStyle(Theme.ink)
                                    Text("Unlimited letters, \(product.displayPrice) per month").font(.footnote).foregroundStyle(Theme.inkSoft)
                                }
                                Spacer()
                                Image(systemName: "chevron.right").font(.footnote.weight(.semibold)).foregroundStyle(Theme.inkFaint)
                            }
                        }
                    }
                }
                Button("Restore purchases") { Task { try? await model.store.restore() } }
            } header: {
                Text("Plan")
            }
            .listRowBackground(Theme.card)

            Section("Your data") {
                Label("Letters are deleted automatically after 30 days. Photos never leave this iPhone.", systemImage: "lock.shield")
                    .font(.callout).foregroundStyle(Theme.inkSoft)
                Button("Delete my account and all letters", role: .destructive) { confirmDelete = true }
            }
            .listRowBackground(Theme.card)

            Section {
                Button("Sign out") { Task { await model.signOut() } }
            } footer: {
                Text("LetterLens gives general information, not legal advice.")
            }
            .listRowBackground(Theme.card)
        }
        .paperBackground()
        .navigationTitle("Settings")
        .toast($toast)
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

struct ProfileHeader: View {
    let name: String?
    let plan: String

    var body: some View {
        HStack(spacing: 14) {
            Text(initial)
                .font(Theme.title(26).weight(.bold)).foregroundStyle(Color(UIColor(hex: 0x1B2540)))
                .frame(width: 60, height: 60)
                .background(Theme.highlighter, in: Circle())
                .overlay(Circle().stroke(Theme.ink, lineWidth: 2.5))
            VStack(alignment: .leading, spacing: 4) {
                Text(name?.isEmpty == false ? name! : "Your account").font(Theme.title(22)).foregroundStyle(Theme.ink)
                Pill(text: plan == "plus" ? "LetterLens Plus" : "Free plan", kind: plan == "plus" ? .ok : .neutral,
                     icon: plan == "plus" ? "sparkles" : nil)
            }
            Spacer()
            LogoMark(size: 40).opacity(0.9)
        }
        .rise(0)
    }

    private var initial: String {
        guard let first = name?.trimmingCharacters(in: .whitespaces).first else { return "✉︎" }
        return String(first).uppercased()
    }
}
