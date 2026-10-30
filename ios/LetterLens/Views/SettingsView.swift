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

