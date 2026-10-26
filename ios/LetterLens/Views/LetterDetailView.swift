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
        .overlay(alignment: .bottom) {
            if let toast {
                Text(toast).padding(12).background(.thinMaterial, in: Capsule()).padding(.bottom, 20)
                    .task { try? await Task.sleep(for: .seconds(2.5)); self.toast = nil }
            }
        }
        .onChange(of: language) { _, code in Task { await switchLanguage(code) } }
        .task {
            language = model.me?.preferredLanguage ?? "en"
            await load()
        }
    }

    @ViewBuilder
    private func content(_ letter: LetterView) -> some View {
        if letter.status != .ready {
            HStack { ProgressView(); Text(letter.status == .failed ? "Processing failed." : "Reading the letter…") }
                .card()
                .task(id: letter.status) {
                    guard letter.status != .failed else { return }
                    try? await Task.sleep(for: .seconds(1.5))
                    await load()
                }
        }
        if letter.degraded {
            Text("The assistant was not fully available. This result uses simple rules; please check everything carefully.")
                .font(.callout).foregroundStyle(Theme.check).card()
        }
        if let explanation = letter.explanation {
            SummaryCard(explanation: explanation, sender: letter.facts?.sender.value) { ids in
                highlighted = Set(ids)
                showOriginal = true
            }
        }
        if let facts = letter.facts {
            if !facts.deadlines.isEmpty {
                Text("Deadlines").font(Theme.title(22))
                ForEach(facts.deadlines) { deadline in
                    DeadlineCard(deadline: deadline, label: letter.explanation?.deadlineLabels[deadline.id] ?? deadline.description,
                                 letterId: letter.id) { toast = $0 }
                }
            }
            if !facts.amounts.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Amounts").font(Theme.title(20))
                    ForEach(facts.amounts) { amount in
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(letter.explanation?.amountLabels[amount.id] ?? amount.description)
                                Text(amount.status == .verified ? "found in the letter" : "please check")
                                    .font(.caption).foregroundStyle(amount.status == .verified ? Theme.inkSoft : Theme.check)
                            }
                            Spacer()
                            Text(formatMoney(amount.value, amount.currency)).font(.system(.headline, design: .serif))
                        }
                    }
                }
                .card()
            }
        }
        if let explanation = letter.explanation, !explanation.nextSteps.isEmpty {
            NextStepsCard(explanation: explanation)
        }
        if letter.status == .ready {
            QuestionCard(letterId: letter.id, language: language)
            Button { showShare = true } label: {
                Label(letter.activeShare == nil ? "Talk to a counsellor" : "Messages with \(letter.activeShare!.tenantName)",
                      systemImage: "person.2.wave.2")
                    .frame(maxWidth: .infinity).padding(.vertical, 6)
            }
            .buttonStyle(.borderedProminent)
        }
        if let disclaimer = letter.explanation?.disclaimer {
            Text(disclaimer).font(.footnote).foregroundStyle(Theme.inkSoft)
        }
    }

    private func load() async {
        do { letter = try await model.api.letter(id: letterId, language: language) } catch {
            model.error = error.localizedDescription
        }
    }

    private func switchLanguage(_ code: String) async {
        guard let letter, !letter.explanationLanguages.contains(code) else { await load(); return }
        do {
            try await model.api.requestExplanation(id: letterId, language: code)
            self.letter?.status = .processing
        } catch {
            model.error = error.localizedDescription
        }
    }
}

struct SummaryCard: View {
    let explanation: Explanation
    let sender: String?
    let showSource: ([String]) -> Void

