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
    @State private var showAllLines = false
    @FocusState private var editorFocused: Bool
    @Namespace private var chips

    private var canSubmit: Bool {
        working == nil && (document != nil || !pasted.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                step(1, "Add the letter").rise(0)
                if let document {
                    recognized(document)
                        .transition(.asymmetric(insertion: .scale(scale: 0.95, anchor: .top).combined(with: .opacity),
                                                removal: .opacity))
                } else {
                    sources.rise(0.05)
                    pasteCard.rise(0.1)
                }

                step(2, "Explain in").rise(0.15)
                languageChips.rise(0.2)

                Label("Text recognition runs on this iPhone. Only the text is sent, processed in the EU and deleted after 30 days.",
                      systemImage: "lock.shield")
                    .font(.footnote).foregroundStyle(Theme.inkSoft)
                    .padding(.top, 4)
                    .rise(0.25)
            }
            .padding(.horizontal).padding(.top, 8).padding(.bottom, 24)
            .animation(Motion.spring, value: document)
        }
        .scrollDismissesKeyboard(.interactively)
        .paperBackground()
        .navigationTitle("New letter")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
            ToolbarItem(placement: .keyboard) {
                HStack { Spacer(); Button("Done") { editorFocused = false } }
            }
        }
        .safeAreaInset(edge: .bottom) {
            Button { Task { await submit() } } label: {
                Label("Explain this letter", systemImage: "sparkle.magnifyingglass")
            }
            .buttonStyle(InkButtonStyle())
            .disabled(!canSubmit)
            .animation(Motion.snappy, value: canSubmit)
            .padding(.horizontal).padding(.top, 12).padding(.bottom, 6)
            .background {
                LinearGradient(colors: [Theme.paper.opacity(0), Theme.paper], startPoint: .top, endPoint: .init(x: 0.5, y: 0.4))
                    .ignoresSafeArea()
            }
        }
        .overlay {
            if let working {
                WorkingOverlay(text: working)
                    .transition(.opacity.combined(with: .scale(scale: 1.04)))
            }
        }
        .animation(Motion.spring, value: working)
        .sensoryFeedback(.success, trigger: document) { old, new in old == nil && new != nil }
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

    // MARK: Parts

    private func step(_ number: Int, _ title: String) -> some View {
        HStack(spacing: 10) {
            Text("\(number)")
                .font(.footnote.weight(.bold)).foregroundStyle(Color(UIColor(hex: 0x1B2540)))
                .frame(width: 26, height: 26)
                .background(Theme.highlighter, in: Circle())
            Text(title).font(Theme.title(21)).foregroundStyle(Theme.ink)
        }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isHeader)
    }

    private var sources: some View {
        HStack(spacing: 12) {
            if DocumentScanner.isAvailable {
                Button { showScanner = true } label: {
                    SourceTile(icon: "doc.viewfinder", title: "Scan", subtitle: "with the camera", prominent: true)
                }
                .buttonStyle(PressableStyle())
            }
            PhotosPicker(selection: $photos, maxSelectionCount: 6, matching: .images) {
                SourceTile(icon: "photo.on.rectangle.angled", title: "Photos", subtitle: "up to 6 pages",
                           prominent: !DocumentScanner.isAvailable)
            }
            .buttonStyle(PressableStyle())
        }
    }

    private var pasteCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Or paste the text", systemImage: "doc.on.clipboard")
                .font(.subheadline.weight(.semibold)).foregroundStyle(Theme.inkSoft)
            ZStack(alignment: .topLeading) {
                if pasted.isEmpty {
                    Text("Sehr geehrte Damen und Herren, …")
                        .font(.system(.body, design: .serif)).foregroundStyle(Theme.inkFaint)
                        .padding(.horizontal, 5).padding(.vertical, 8)
                        .allowsHitTesting(false)
                }
                TextEditor(text: $pasted)
                    .font(.system(.body, design: .serif))
                    .scrollContentBackground(.hidden)
                    .focused($editorFocused)
                    .frame(minHeight: 130)
            }
            .padding(6)
            .background(Theme.paper.opacity(0.6), in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12)
                .stroke(editorFocused ? Theme.ink : Theme.line, lineWidth: editorFocused ? 1.5 : 1))
            .animation(Motion.snappy, value: editorFocused)
        }
        .card()
    }

    private func recognized(_ document: LetterDocument) -> some View {
        let lines = document.lines.map(\.text)
        let shown = showAllLines ? lines : Array(lines.prefix(8))
        return VStack(alignment: .leading, spacing: 12) {
            HStack {
                Pill(text: "\(lines.count) lines recognized", kind: .ok, icon: "text.viewfinder")
                Spacer()
                Button(role: .destructive) {
                    withAnimation(Motion.spring) { self.document = nil; photos = [] }
                } label: { Label("Discard", systemImage: "trash") }
                .font(.subheadline.weight(.semibold)).foregroundStyle(Theme.danger)
            }
            VStack(alignment: .leading, spacing: 3) {
                ForEach(Array(shown.enumerated()), id: \.offset) { index, line in
                    Text(line)
                        .font(.system(.footnote, design: .serif)).foregroundStyle(Theme.ink)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .rise(index: index, base: 0.1)
                }
                if lines.count > 8 {
                    Button(showAllLines ? "Show less" : "Show all \(lines.count) lines") {
                        withAnimation(Motion.spring) { showAllLines.toggle() }
                    }
                    .font(.footnote.weight(.semibold)).foregroundStyle(Theme.link).padding(.top, 6)
                }
            }
            .textSelection(.enabled)
            .environment(\.locale, Locale(identifier: "de"))
            .padding(14)
            .background(Theme.paper.opacity(0.6), in: RoundedRectangle(cornerRadius: 10))
            .overlay(alignment: .top) {
                // A highlighter strip along the top, so the block reads as the scanned letter.
                Rectangle().fill(Theme.highlighter).frame(height: 3).clipShape(Capsule()).padding(.horizontal, 30).offset(y: -1.5)
            }
        }
        .card()
    }

    private var languageChips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(model.languages) { lang in
                    let selected = lang.code == language
                    Button {
                        withAnimation(Motion.snappy) { language = lang.code }
                    } label: {
                        HStack(spacing: 5) {
                            if selected { Image(systemName: "checkmark").font(.caption.weight(.bold)).transition(.scale) }
                            Text(lang.nativeName)
                            if lang.status == "experimental" {
                                Text("beta").font(.caption2.weight(.bold)).padding(.horizontal, 5).padding(.vertical, 1)
                                    .background(selected ? Theme.card.opacity(0.2) : Theme.paperDeep, in: Capsule())
                            }
                        }
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(selected ? Theme.card : Theme.ink)
                        .padding(.horizontal, 14).padding(.vertical, 10)
                        .background {
                            if selected {
                                Capsule().fill(Theme.ink).matchedGeometryEffect(id: "chip", in: chips)
                            } else {
                                Capsule().fill(Theme.card).overlay(Capsule().stroke(Theme.line))
                            }
                        }
                    }
                    .buttonStyle(PressableStyle())
                    .accessibilityAddTraits(selected ? .isSelected : [])
                }
            }
            .padding(.vertical, 4).padding(.horizontal, 2)
        }
        .sensoryFeedback(.selection, trigger: language)
    }

    // MARK: Actions

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

    private func recognize(_ images: [CGImage]) async {
        working = "Reading the letter on this iPhone…"
        defer { working = nil }
        do {
            let result = try await TextRecognizer.recognize(images)
            if result.lines.isEmpty {
                model.error = "No text was found. Try again with more light and the whole page in view."
            } else {
                document = result
            }
        } catch {
            model.error = error.localizedDescription
        }
    }

    private func submit() async {
        editorFocused = false
        let doc = document ?? DocumentBuilder.fromText(pasted)
        guard !doc.lines.isEmpty else { return }
        working = "Sending…"
        defer { working = nil }
        do {
            _ = try await model.api.createLetter(doc, language: language, idempotencyKey: idempotencyKey)
            await model.loadProfile()
            dismiss()
        } catch {
            model.error = error.localizedDescription
        }
    }
}

struct SourceTile: View {
    let icon: String
    let title: String
    let subtitle: String
    var prominent = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Image(systemName: icon)
                .font(.title2.weight(.semibold))
                .foregroundStyle(prominent ? Color(UIColor(hex: 0x1B2540)) : Theme.ink)
                .frame(width: 50, height: 50)
                .background(prominent ? Theme.highlighter : Theme.paperDeep, in: RoundedRectangle(cornerRadius: 14))
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(Theme.title(20)).foregroundStyle(prominent ? Theme.card : Theme.ink)
                Text(subtitle).font(.footnote).foregroundStyle(prominent ? Theme.card.opacity(0.75) : Theme.inkSoft)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, minHeight: 150, alignment: .topLeading)
        .background {
            RoundedRectangle(cornerRadius: 18, style: .continuous).fill(prominent ? Theme.ink : Theme.card)
        }
        .overlay(RoundedRectangle(cornerRadius: 18, style: .continuous).stroke(prominent ? .clear : Theme.line))
        .shadow(color: Theme.ink.opacity(prominent ? 0.25 : 0.08), radius: 14, y: 8)
        .accessibilityElement(children: .combine)
    }
}

/// Covers the screen while photos are read or the letter is sent.
struct WorkingOverlay: View {
    let text: String

    var body: some View {
        ZStack {
            Rectangle().fill(.ultraThinMaterial).ignoresSafeArea()
            VStack(spacing: 18) {
                ReadingArt(width: 200)
                Text(text).font(Theme.title(20)).foregroundStyle(Theme.ink).multilineTextAlignment(.center)
                    .contentTransition(.opacity)
            }
            .padding(28)
            .background(Theme.card, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 24, style: .continuous).stroke(Theme.line))
            .shadow(color: Theme.ink.opacity(0.2), radius: 30, y: 16)
            .padding(32)
        }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.updatesFrequently)
    }
}
