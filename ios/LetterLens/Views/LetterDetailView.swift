import LetterLensCore
import SwiftUI

struct LetterDetailView: View {
    let letterId: String
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var letter: LetterView?
    @State private var language = "en"
    @State private var highlighted: Set<String> = []
    @State private var showOriginal = false
    @State private var showShare = false
    @State private var confirmDelete = false
    @State private var toast: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let letter {
                    content(letter)
                } else {
                    ProgressView().frame(maxWidth: .infinity).padding(.top, 80)
                }
            }
            .padding()
        }
        .paperBackground()
        .navigationTitle(LetterTypes.names[letter?.classification?.letterType ?? "other"] ?? "Letter")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Menu {
                    Picker("Language", selection: $language) {
                        ForEach(model.languages) { Text($0.nativeName).tag($0.code) }
                    }
                    Button { showOriginal = true } label: { Label("Original letter", systemImage: "doc.text") }
                    Button(role: .destructive) { confirmDelete = true } label: { Label("Delete letter", systemImage: "trash") }
                } label: { Image(systemName: "ellipsis.circle") }
            }
        }
        .sheet(isPresented: $showOriginal) { OriginalSheet(lines: letter?.lines ?? [], highlighted: highlighted) }
        .sheet(isPresented: $showShare, onDismiss: { Task { await load() } }) {
            if let letter { ShareSheet(letter: letter) }
        }
        .confirmationDialog("Delete this letter and its results?", isPresented: $confirmDelete, titleVisibility: .visible) {
            Button("Delete", role: .destructive) {
                Task {
                    try? await model.api.deleteLetter(id: letterId)
                    dismiss()
                }
            }
        }
