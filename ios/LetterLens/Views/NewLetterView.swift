import LetterLensCore
import PhotosUI
import SwiftUI

struct NewLetterView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var showScanner = false
    @State private var photos: [PhotosPickerItem] = []
    @State private var document: LetterDocument?
    @State private var pasted = ""
    @State private var language = "en"
    @State private var working: String?
    @State private var idempotencyKey = UUID().uuidString

    var body: some View {
        Form {
            Section {
                if DocumentScanner.isAvailable {
                    Button { showScanner = true } label: { Label("Scan with the camera", systemImage: "doc.viewfinder") }
                }
                PhotosPicker(selection: $photos, maxSelectionCount: 6, matching: .images) {
                    Label("Choose photos", systemImage: "photo.on.rectangle")
                }
            } footer: {
                Text("Text recognition runs on this iPhone. Only the text is sent, processed in the EU and deleted after 30 days.")
            }

            if let document {
                Section("Recognized text (\(document.lines.count) lines)") {
                    Text(document.lines.map(\.text).joined(separator: "\n"))
                        .font(.system(.footnote, design: .serif)).textSelection(.enabled)
                        .environment(\.locale, Locale(identifier: "de"))
                    Button("Discard", role: .destructive) { self.document = nil }
                }
            } else {
                Section("Or paste the text") {
                    TextEditor(text: $pasted).frame(minHeight: 120)
                }
            }

            Section {
                Picker("Explain in", selection: $language) {
                    ForEach(model.languages) { lang in
                        Text(lang.status == "experimental" ? "\(lang.nativeName) · beta" : lang.nativeName).tag(lang.code)
                    }
                }
            }

            if let working {
                Section { HStack { ProgressView(); Text(working) } }
            }
        }
        .paperBackground()
        .navigationTitle("New letter")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
            ToolbarItem(placement: .confirmationAction) {
                Button("Explain") { Task { await submit() } }
                    .disabled(working != nil || (document == nil && pasted.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty))
            }
        }
        .fullScreenCover(isPresented: $showScanner) {
            DocumentScanner(onFinish: { images in
                showScanner = false
                Task { await recognize(images) }
            }, onCancel: { showScanner = false })
            .ignoresSafeArea()
        }
        .onChange(of: photos) { _, items in Task { await loadPhotos(items) } }
        .onAppear { language = model.me?.preferredLanguage ?? "en" }
    }

    private func loadPhotos(_ items: [PhotosPickerItem]) async {
        guard !items.isEmpty else { return }
        working = "Loading photos…"
        var images: [CGImage] = []
        for item in items {
            if let data = try? await item.loadTransferable(type: Data.self), let image = UIImage(data: data)?.cgImage {
                images.append(image)
            }
        }
        await recognize(images)
    }

