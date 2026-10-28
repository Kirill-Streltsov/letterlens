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

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let sender { Text(sender).font(.caption).foregroundStyle(Theme.inkSoft) }
            Text(explanation.headline).font(Theme.title(24)).foregroundStyle(Theme.ink)
            Text(explanation.letterKind).foregroundStyle(Theme.inkSoft)
            ForEach(Array(explanation.summary.enumerated()), id: \.offset) { _, sentence in
                Button { showSource(sentence.lineIds) } label: {
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Circle().fill(Theme.marker).frame(width: 8, height: 8)
                        Text(sentence.text).multilineTextAlignment(.leading).foregroundStyle(Theme.ink)
                    }
                }
                .buttonStyle(.plain)
                .accessibilityHint("Shows this sentence in the original letter")
            }
        }
        .environment(\.layoutDirection, explanation.language == "ar" ? .rightToLeft : .leftToRight)
        .card()
    }
}

struct DeadlineCard: View {
    let deadline: VerifiedDeadline
    let label: String
    let letterId: String
    let notify: (String) -> Void

    var body: some View {
        HStack(spacing: 0) {
            Rectangle().fill(deadline.status == .verified ? Theme.ok : Theme.check).frame(width: 5)
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Pill(text: deadline.status == .verified ? "Found in the letter" : "Please check",
                         kind: deadline.status == .verified ? .ok : .check)
                    if let pill = Pill.deadline(iso: deadline.dueDate, status: deadline.status.rawValue) { pill }
                }
                Text(formatDate(deadline.dueDate)).font(Theme.title(22))
                Text(label)
                if let note = deadline.note { Text(note).font(.caption).foregroundStyle(Theme.inkSoft) }
                if let rule = deadline.rule {
                    DisclosureGroup("How this date was estimated") { Text(rule).font(.caption) }.font(.caption)
                }
                if let iso = deadline.dueDate {
                    HStack {
                        Button("Add to calendar") {
                            Task {
                                do {
                                    let prefix = deadline.status == .verified ? "" : "PLEASE CHECK THIS DATE. "
                                    try await ReminderService.addToCalendar(title: label, iso: iso,
                                                                            notes: prefix + (deadline.sourceText ?? ""))
                                    notify("Added to your calendar")
                                } catch { notify(error.localizedDescription) }
                            }
                        }
                        Button("Remind me") {
                            Task {
                                let when = try? await ReminderService.scheduleReminder(id: "\(letterId)-\(deadline.id)",
                                                                                     title: label, iso: iso)
                                notify(when.map { "Reminder on \($0.formatted(date: .abbreviated, time: .shortened))" }
                                       ?? "Reminders are turned off for LetterLens")
                            }
                        }
                    }
                    .buttonStyle(.bordered).font(.callout)
                }
            }
            .padding(14)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.card, in: RoundedRectangle(cornerRadius: 14))
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.line))
    }
}

struct NextStepsCard: View {
    let explanation: Explanation

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("What people usually do next").font(Theme.title(20))
            ForEach(Array(explanation.nextSteps.enumerated()), id: \.offset) { _, step in
                Text("• \(step.text) " + step.citationIds.map { "[\($0.dropFirst())]" }.joined())
            }
            ForEach(explanation.citations) { citation in
                if let url = URL(string: citation.sourceUrl) {
                    Link("[\(citation.id.dropFirst())] \(citation.title) (\(citation.sourceName))", destination: url)
                        .font(.caption)
                }
            }
            Text(explanation.counsellingHint).font(.callout).padding(10)
                .background(Theme.paperDeep, in: RoundedRectangle(cornerRadius: 10))
        }
        .environment(\.layoutDirection, explanation.language == "ar" ? .rightToLeft : .leftToRight)
        .card()
    }
}

struct QuestionCard: View {
    let letterId: String
    let language: String
    @Environment(AppModel.self) private var model
    @State private var question = ""
    @State private var answer: QuestionResponse?
    @State private var busy = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Ask about this letter").font(Theme.title(20))
            HStack {
                TextField("What does “Bekanntgabe” mean?", text: $question).textFieldStyle(.roundedBorder)
                Button("Ask") {
                    busy = true
                    Task {
                        defer { busy = false }
                        do { answer = try await model.api.ask(id: letterId, question: question, language: language) } catch {
                            model.error = error.localizedDescription
                        }
                    }
                }
                .disabled(busy || question.count < 3)
            }
            if let answer {
                Text(answer.answer ?? "I could not check this answer against the letter. Please ask a counsellor.")
                    .padding(10).frame(maxWidth: .infinity, alignment: .leading)
                    .background(answer.refused ? Theme.check.opacity(0.15) : Theme.paperDeep, in: RoundedRectangle(cornerRadius: 10))
            }
            Text("General information only. LetterLens does not tell you what to decide in your case.")
                .font(.caption).foregroundStyle(Theme.inkSoft)
        }
        .card()
    }
}

struct OriginalSheet: View {
    let lines: [OcrLine]
    let highlighted: Set<String>
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 2) {
                        ForEach(lines) { line in
                            Text(line.text)
                                .font(.system(.body, design: .serif))
                                .padding(.horizontal, 6).padding(.vertical, 2)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(highlighted.contains(line.id) ? Theme.marker : .clear, in: RoundedRectangle(cornerRadius: 4))
                                .id(line.id)
                        }
                    }
                    .padding()
                    .card()
                    .padding()
                }
                .onAppear { if let first = lines.first(where: { highlighted.contains($0.id) }) { proxy.scrollTo(first.id, anchor: .center) } }
            }
            .paperBackground()
            .navigationTitle("Original letter")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { Button("Done") { dismiss() } }
        }
    }
}

struct MessageBubble: View {
    let message: Message
    private var mine: Bool { message.authorRole == "client" }

    var body: some View {
        VStack(alignment: mine ? .trailing : .leading, spacing: 2) {
            Text(message.text)
                .padding(10)
                .background(mine ? Theme.ink.opacity(0.12) : Theme.paperDeep, in: RoundedRectangle(cornerRadius: 12))
            if let original = message.originalText {
                Text(original).font(.caption2).foregroundStyle(Theme.inkSoft)
            }
        }
        .frame(maxWidth: .infinity, alignment: mine ? .trailing : .leading)
    }
}

struct ShareSheet: View {
    static func label(for service: CounsellingService) -> String {
        guard let city = service.city else { return service.name }
        return "\(service.name) (\(city))"
    }

    let letter: LetterView
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var services: [CounsellingService] = []
    @State private var selected: String?
    @State private var consent = false
    @State private var messages: [Message] = []
    @State private var text = ""

    var body: some View {
        NavigationStack {
            Form {
                if let share = letter.activeShare {
                    Section("Shared with \(share.tenantName)") {
                        ForEach(messages) { MessageBubble(message: $0) }
                        HStack {
                            TextField("Message", text: $text)
                            Button("Send") {
                                Task {
                                    if let sent = try? await model.api.sendMessage(shareId: share.id, text: text) {
                                        messages.append(sent); text = ""
                                    }
                                }
                            }.disabled(text.isEmpty)
                        }
                    }
                    Section {
                        Button("Stop sharing", role: .destructive) {
                            Task { try? await model.api.revokeShare(id: share.id); dismiss() }
                        }
                    }
                } else {
                    Section {
                        Picker("Counselling service", selection: $selected) {
                            Text("Choose…").tag(String?.none)
                            ForEach(services) { service in
                                Text(Self.label(for: service)).tag(Optional(service.id))
                            }
                        }
                        Toggle(isOn: $consent) {
                            Text("I agree that this counselling service can see the text of this letter, the summary and my messages for 30 days. I can stop sharing at any time.")
                                .font(.callout)
                        }
                    } footer: {
                        Text("Free counselling services can check your individual case. Consent version share-consent-v1.")
                    }
                    Section {
                        Button("Share") {
                            Task {
                                guard let selected else { return }
                                do { _ = try await model.api.share(letterId: letter.id, tenantId: selected); dismiss() } catch {
                                    model.error = error.localizedDescription
                                }
                            }
                        }
                        .disabled(selected == nil || !consent)
                    }
                }
            }
            .paperBackground()
            .navigationTitle("Counselling")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { Button("Close") { dismiss() } }
            .task {
                if let share = letter.activeShare {
                    messages = (try? await model.api.messages(shareId: share.id)) ?? []
                } else {
                    services = (try? await model.api.counsellingServices()) ?? []
                }
            }
        }
    }
}
