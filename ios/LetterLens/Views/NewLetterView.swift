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

