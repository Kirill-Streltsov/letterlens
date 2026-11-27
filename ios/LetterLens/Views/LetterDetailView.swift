import LetterLensCore
import SwiftUI

struct LetterDetailView: View {
    let letterId: String
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var letter: LetterView?
    @State private var language = "en"
    /// Set while the app (not the reader) changes `language`, so onChange does not start a new run.
    @State private var syncingLanguage = false
    @State private var userPickedLanguage = false
    @State private var highlighted: Set<String> = []
    @State private var showOriginal = false
    @State private var showShare = false
    @State private var confirmDelete = false
    @State private var toast: Toast?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let letter {
                    content(letter)
                } else {
                    VStack(spacing: 14) {
                        VStack(alignment: .leading, spacing: 12) {
                            SkeletonBar(width: 120, height: 10)
                            SkeletonBar(height: 22).frame(maxWidth: .infinity)
                            SkeletonBar(width: 200, height: 22)
                            ForEach(0..<3, id: \.self) { _ in SkeletonBar(height: 12).frame(maxWidth: .infinity) }
                        }
                        .shimmer().card()
                        SkeletonRow()
                    }
                    .rise(0)
                }
            }
            .padding(.horizontal).padding(.top, 8).padding(.bottom, 32)
            .animation(Motion.spring, value: letter?.status)
        }
        .paperBackground()
        .navigationTitle(LetterTypes.names[letter?.classification?.letterType ?? "other"] ?? "Letter")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Menu {
                    Picker(selection: $language) {
                        ForEach(model.languages) { Text($0.nativeName).tag($0.code) }
                    } label: { Label("Language", systemImage: "globe") }
                    .pickerStyle(.menu)
                    Button { highlighted = []; showOriginal = true } label: { Label("Original letter", systemImage: "doc.text") }
                    Divider()
                    Button(role: .destructive) { confirmDelete = true } label: { Label("Delete letter", systemImage: "trash") }
                } label: { Image(systemName: "ellipsis") }
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
        .toast($toast)
        .onChange(of: language) { _, code in
            if syncingLanguage { syncingLanguage = false; return }
            userPickedLanguage = true
            Task { await switchLanguage(code) }
        }
        .task {
            language = model.me?.preferredLanguage ?? "en"
            await load()
        }
    }

    @ViewBuilder
    private func content(_ letter: LetterView) -> some View {
        if letter.status != .ready {
            ProcessingCard(failed: letter.status == .failed, translating: letter.explanation != nil)
                .transition(.scale(scale: 0.95).combined(with: .opacity))
                .task(id: letter.status) {
                    guard letter.status != .failed else { return }
                    try? await Task.sleep(for: .seconds(1.5))
                    await load()
                }
        }
        if letter.degraded {
            Notice(icon: "exclamationmark.triangle.fill",
                   text: "The assistant was not fully available. This result uses simple rules; please check everything carefully.")
                .rise(0.05)
        }
        if let explanation = letter.explanation {
            SummaryCard(explanation: explanation, sender: letter.facts?.sender.value,
                        letterType: letter.classification?.letterType) { ids in
                highlighted = Set(ids)
                showOriginal = true
            }
            .rise(0.05)
            .id(explanation.language)
            .transition(.opacity)
        }
        if let facts = letter.facts {
            if !facts.deadlines.isEmpty {
                SectionTitle(text: "Deadlines", count: facts.deadlines.count, icon: "calendar").rise(0.12)
                ForEach(Array(facts.deadlines.enumerated()), id: \.element.id) { index, deadline in
                    DeadlineCard(deadline: deadline, label: letter.explanation?.deadlineLabels[deadline.id] ?? deadline.description,
                                 letterId: letter.id) { toast = $0 }
                        .rise(index: index, base: 0.16)
                }
            }
            if !facts.amounts.isEmpty {
                AmountsCard(amounts: facts.amounts, labels: letter.explanation?.amountLabels ?? [:]).rise(0.22)
            }
        }
        if let explanation = letter.explanation, !explanation.nextSteps.isEmpty {
            NextStepsCard(explanation: explanation).rise(0.28)
        }
        if letter.status == .ready {
            QuestionCard(letterId: letter.id, language: language).rise(0.32)
            Button { showShare = true } label: {
                Label(letter.activeShare == nil ? "Talk to a counsellor" : "Messages with \(letter.activeShare!.tenantName)",
                      systemImage: "person.2.wave.2")
            }
            .buttonStyle(InkButtonStyle())
            .padding(.top, 4)
            .rise(0.36)
        }
        if let disclaimer = letter.explanation?.disclaimer {
            Text(disclaimer).font(.footnote).foregroundStyle(Theme.inkFaint).padding(.horizontal, 4).rise(0.4)
        }
    }

    private func load() async {
        do {
            let loaded = try await model.api.letter(id: letterId, language: language)
            withAnimation(Motion.spring) { letter = loaded }
            // Until the reader picks a language, show the language of the explanation that exists.
            if !userPickedLanguage, let shown = loaded.explanation?.language, shown != language {
                syncingLanguage = true
                language = shown
            }
        } catch {
            model.error = error.localizedDescription
        }
    }

    private func switchLanguage(_ code: String) async {
        guard let letter, !letter.explanationLanguages.contains(code) else { await load(); return }
        do {
            try await model.api.requestExplanation(id: letterId, language: code)
            withAnimation(Motion.spring) { self.letter?.status = .processing }
        } catch {
            model.error = error.localizedDescription
        }
    }
}

// MARK: - Cards

struct ProcessingCard: View {
    let failed: Bool
    var translating = false

    var body: some View {
        VStack(spacing: 14) {
            if failed {
                Image(systemName: "exclamationmark.triangle.fill").font(.system(size: 36)).foregroundStyle(Theme.check)
                Text("Processing failed.").font(Theme.title(20)).foregroundStyle(Theme.ink)
                Text("Please try again with a new scan, or paste the text.")
                    .font(.subheadline).foregroundStyle(Theme.inkSoft).multilineTextAlignment(.center)
            } else {
                ReadingArt(width: 190)
                Text(translating ? "Writing the explanation…" : "Reading the letter…")
                    .font(Theme.title(20)).foregroundStyle(Theme.ink)
                Text("Dates and amounts are checked against the letter itself.")
                    .font(.subheadline).foregroundStyle(Theme.inkSoft).multilineTextAlignment(.center)
            }
        }
        .frame(maxWidth: .infinity)
        .card(padding: 22)
        .accessibilityElement(children: .combine)
    }
}

struct Notice: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: icon)
            Text(text).fixedSize(horizontal: false, vertical: true)
        }
        .font(.callout.weight(.medium))
        .foregroundStyle(Theme.check)
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.checkBg, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

struct SummaryCard: View {
    let explanation: Explanation
    let sender: String?
    var letterType: String?
    let showSource: ([String]) -> Void
    @State private var tapped: Int?

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 12) {
                TypeBadge(letterType: letterType, size: 38)
                VStack(alignment: .leading, spacing: 1) {
                    if let sender { Text(sender).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink).lineLimit(1) }
                    Text(explanation.letterKind).font(.caption).foregroundStyle(Theme.inkSoft).lineLimit(2)
                }
            }
            Text(explanation.headline).font(Theme.title(25)).foregroundStyle(Theme.ink)
                .fixedSize(horizontal: false, vertical: true)
            VStack(alignment: .leading, spacing: 6) {
                ForEach(Array(explanation.summary.enumerated()), id: \.offset) { index, sentence in
                    let linked = !sentence.lineIds.isEmpty
                    Button {
                        guard linked else { return }
                        withAnimation(Motion.snappy) { tapped = index }
                        Task {
                            try? await Task.sleep(for: .milliseconds(220))
                            showSource(sentence.lineIds)
                            try? await Task.sleep(for: .milliseconds(600))
                            withAnimation(.easeOut) { tapped = nil }
                        }
                    } label: {
                        HStack(alignment: .firstTextBaseline, spacing: 10) {
                            Circle().fill(linked ? Theme.marker : Theme.line).frame(width: 9, height: 9)
                                .overlay(Circle().stroke(Theme.ink.opacity(0.12)))
                            Text(sentence.text).multilineTextAlignment(.leading)
                                .foregroundStyle(linked ? Theme.ink : Theme.inkSoft)
                                .fixedSize(horizontal: false, vertical: true)
                            Spacer(minLength: 0)
                        }
                        .padding(.horizontal, 8).padding(.vertical, 6)
                        .background(tapped == index ? Theme.markerSoft : .clear, in: RoundedRectangle(cornerRadius: 8))
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(PressableStyle())
                    .padding(.horizontal, -8)
                    .accessibilityHint(linked ? "Shows this sentence in the original letter" : "")
                }
            }
            if explanation.summary.contains(where: { !$0.lineIds.isEmpty }) {
                Label("Tap a sentence to see it in the letter", systemImage: "hand.point.up.left")
                    .font(.caption).foregroundStyle(Theme.inkFaint)
            }
        }
        .environment(\.layoutDirection, explanation.language == "ar" ? .rightToLeft : .leftToRight)
        .card(padding: 18)
        .sensoryFeedback(.selection, trigger: tapped) { _, new in new != nil }
    }
}

struct DeadlineCard: View {
    let deadline: VerifiedDeadline
    let label: String
    let letterId: String
    let notify: (Toast) -> Void
    @State private var showRule = false

    private var accent: Color { deadline.status == .verified ? Theme.ok : Theme.check }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Pill(text: deadline.status == .verified ? "Found in the letter" : "Please check",
                     kind: deadline.status == .verified ? .ok : .check,
                     icon: deadline.status == .verified ? "checkmark" : "questionmark")
                if let pill = Pill.deadline(iso: deadline.dueDate, status: deadline.status.rawValue) { pill }
            }
            Text(formatDate(deadline.dueDate)).font(Theme.title(24)).foregroundStyle(Theme.ink)
            Text(label).foregroundStyle(Theme.ink).fixedSize(horizontal: false, vertical: true)
            if let note = deadline.note { Text(note).font(.caption).foregroundStyle(Theme.inkSoft) }
            if let rule = deadline.rule {
                Button {
                    withAnimation(Motion.spring) { showRule.toggle() }
                } label: {
                    HStack(spacing: 4) {
                        Text("How this date was estimated")
                        Image(systemName: "chevron.down").rotationEffect(.degrees(showRule ? 180 : 0))
                    }
                    .font(.caption.weight(.semibold)).foregroundStyle(Theme.link)
                }
                .buttonStyle(.plain)
                if showRule {
                    Text(rule).font(.caption).foregroundStyle(Theme.inkSoft)
                        .padding(10).frame(maxWidth: .infinity, alignment: .leading)
                        .background(Theme.paperDeep, in: RoundedRectangle(cornerRadius: 10))
                        .transition(.move(edge: .top).combined(with: .opacity))
                }
            }
            if let iso = deadline.dueDate {
                HStack(spacing: 8) {
                    Button {
                        Task {
                            do {
                                let prefix = deadline.status == .verified ? "" : "PLEASE CHECK THIS DATE. "
                                try await ReminderService.addToCalendar(title: label, iso: iso,
                                                                        notes: prefix + (deadline.sourceText ?? ""))
                                notify(Toast(text: "Added to your calendar", icon: "calendar.badge.checkmark"))
                            } catch { notify(Toast(text: error.localizedDescription, icon: "xmark.octagon.fill", isError: true)) }
                        }
                    } label: { Label("Add to calendar", systemImage: "calendar.badge.plus") }
                    Button {
                        Task {
                            let when = try? await ReminderService.scheduleReminder(id: "\(letterId)-\(deadline.id)",
                                                                                 title: label, iso: iso)
                            notify(when.map {
                                Toast(text: "Reminder on \($0.formatted(date: .abbreviated, time: .shortened))", icon: "bell.badge.fill")
                            } ?? Toast(text: "Reminders are turned off for LetterLens", icon: "bell.slash.fill", isError: true))
                        }
                    } label: { Label("Remind me", systemImage: "bell") }
                }
                .buttonStyle(ChipButtonStyle())
                .padding(.top, 2)
            }
        }
        .padding(16).padding(.leading, 5)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.card, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(alignment: .leading) { Rectangle().fill(accent).frame(width: 5) }
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(Theme.line))
        .shadow(color: Theme.ink.opacity(0.10), radius: 14, y: 8)
    }
}

struct AmountsCard: View {
    let amounts: [VerifiedAmount]
    let labels: [String: String]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            SectionTitle(text: "Amounts", icon: "eurosign.circle").padding(.bottom, 6)
            ForEach(Array(amounts.enumerated()), id: \.element.id) { index, amount in
                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(labels[amount.id] ?? amount.description).foregroundStyle(Theme.ink)
                        Label(amount.status == .verified ? "found in the letter" : "please check",
                              systemImage: amount.status == .verified ? "checkmark.circle.fill" : "questionmark.circle.fill")
                            .font(.caption).foregroundStyle(amount.status == .verified ? Theme.ok : Theme.check)
                    }
                    Spacer()
                    Text(formatMoney(amount.value, amount.currency))
                        .font(.system(.title3, design: .serif).weight(.bold)).foregroundStyle(Theme.ink)
                        .padding(.horizontal, 6)
                        .background(alignment: .bottom) {
                            Capsule().fill(Theme.marker.opacity(0.7)).frame(height: 9).offset(y: -3)
                        }
                }
                .padding(.vertical, 12)
                if index < amounts.count - 1 {
                    Line().stroke(Theme.line, style: StrokeStyle(lineWidth: 1, dash: [4, 4])).frame(height: 1)
                }
            }
        }
        .card()
    }

    private struct Line: Shape {
        func path(in rect: CGRect) -> Path { Path { $0.move(to: .zero); $0.addLine(to: CGPoint(x: rect.width, y: 0)) } }
    }
}

struct NextStepsCard: View {
    let explanation: Explanation

    /// Citation number = position in the source list (not the internal passage id).
    private func number(_ id: String) -> Int? {
        explanation.citations.firstIndex { $0.id == id }.map { $0 + 1 }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionTitle(text: "What people usually do next", icon: "signpost.right")
            ForEach(Array(explanation.nextSteps.enumerated()), id: \.offset) { index, step in
                HStack(alignment: .firstTextBaseline, spacing: 12) {
                    Text("\(index + 1)")
                        .font(.caption.weight(.bold)).foregroundStyle(Theme.card)
                        .frame(width: 22, height: 22).background(Theme.ink, in: Circle())
                        .alignmentGuide(.firstTextBaseline) { $0[VerticalAlignment.center] + 5 }
                    Text(step.text + " " + step.citationIds.compactMap { id in number(id).map { "[\($0)]" } }.joined())
                        .foregroundStyle(Theme.ink).fixedSize(horizontal: false, vertical: true)
                }
            }
            if !explanation.citations.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(explanation.citations) { citation in
                        if let url = URL(string: citation.sourceUrl) {
                            Link(destination: url) {
                                HStack(alignment: .firstTextBaseline, spacing: 6) {
                                    Text("[\(number(citation.id) ?? 0)]").monospacedDigit()
                                    Text("\(citation.title) (\(citation.sourceName))").multilineTextAlignment(.leading)
                                    Image(systemName: "arrow.up.right").font(.caption2)
                                }
                                .font(.caption).foregroundStyle(Theme.link)
                            }
                        }
                    }
                }
                .padding(.top, 2)
            }
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "person.2.fill").foregroundStyle(Theme.inkSoft)
                Text(explanation.counsellingHint).font(.callout).foregroundStyle(Theme.ink)
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.paperDeep, in: RoundedRectangle(cornerRadius: 12))
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
    @State private var asked = ""
    @State private var busy = false
    @FocusState private var focused: Bool

    private var canAsk: Bool { !busy && question.trimmingCharacters(in: .whitespaces).count >= 3 }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionTitle(text: "Ask about this letter", icon: "bubble.left.and.text.bubble.right")
            HStack(spacing: 8) {
                TextField("What does “Bekanntgabe” mean?", text: $question)
                    .focused($focused)
                    .submitLabel(.send)
                    .onSubmit { if canAsk { ask() } }
                    .padding(.leading, 16).padding(.vertical, 12)
                Button(action: ask) {
                    Image(systemName: "arrow.up")
                        .font(.body.weight(.bold)).foregroundStyle(Theme.card)
                        .frame(width: 36, height: 36)
                        .background(Theme.ink, in: Circle())
                }
                .disabled(!canAsk)
                .opacity(canAsk ? 1 : 0.35)
                .scaleEffect(canAsk ? 1 : 0.85)
                .animation(Motion.bouncy, value: canAsk)
                .padding(.trailing, 5)
                .accessibilityLabel("Ask")
            }
            .background(Theme.paper.opacity(0.7), in: Capsule())
            .overlay(Capsule().stroke(focused ? Theme.ink : Theme.line, lineWidth: focused ? 1.5 : 1))
            .animation(Motion.snappy, value: focused)

            if busy {
                HStack(spacing: 10) {
                    TypingDots()
                    Text("Checking the letter…").font(.subheadline).foregroundStyle(Theme.inkSoft)
                }
                .padding(12)
                .background(Theme.paperDeep, in: RoundedRectangle(cornerRadius: 14))
                .transition(.scale(scale: 0.9, anchor: .topLeading).combined(with: .opacity))
            } else if let answer {
                VStack(alignment: .leading, spacing: 8) {
                    Text(asked).font(.caption.weight(.semibold)).foregroundStyle(Theme.inkSoft)
                    Text(answer.answer ?? "I could not check this answer against the letter. Please ask a counsellor.")
                        .foregroundStyle(answer.refused ? Theme.check : Theme.ink)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(14).frame(maxWidth: .infinity, alignment: .leading)
                .background(answer.refused ? Theme.checkBg : Theme.paperDeep, in: RoundedRectangle(cornerRadius: 14))
                .transition(.scale(scale: 0.9, anchor: .topLeading).combined(with: .opacity))
            }
            Text("General information only. LetterLens does not tell you what to decide in your case.")
                .font(.caption).foregroundStyle(Theme.inkFaint)
        }
        .card()
        .animation(Motion.spring, value: busy)
        .sensoryFeedback(.success, trigger: answer?.answer) { _, new in new != nil }
    }

    private func ask() {
        focused = false
        busy = true
        asked = question
        Task {
            defer { busy = false }
            do {
                answer = try await model.api.ask(id: letterId, question: question, language: language)
                question = ""
            } catch {
                model.error = error.localizedDescription
            }
        }
    }
}

/// Three dots that bounce in turn while an answer is on its way.
struct TypingDots: View {
    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3, id: \.self) { index in
                Circle().fill(Theme.inkSoft).frame(width: 7, height: 7)
                    .phaseAnimator([0.0, -5.0, 0.0]) { dot, y in dot.offset(y: y) } animation: { _ in
                        .easeInOut(duration: 0.3).delay(Double(index) * 0.12)
                    }
            }
        }
        .accessibilityHidden(true)
    }
}

// MARK: - Sheets

struct OriginalSheet: View {
    let lines: [OcrLine]
    let highlighted: Set<String>
    @Environment(\.dismiss) private var dismiss
    @State private var marked = false

    var body: some View {
        NavigationStack {
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 2) {
                        ForEach(lines) { line in
                            let hit = highlighted.contains(line.id)
                            Text(line.text)
                                .font(.system(.body, design: .serif))
                                .foregroundStyle(Theme.ink)
                                .padding(.horizontal, 6).padding(.vertical, 2)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(alignment: .leading) {
                                    if hit {
                                        RoundedRectangle(cornerRadius: 4).fill(Theme.marker)
                                            .scaleEffect(x: marked ? 1 : 0, anchor: .leading)
                                    }
                                }
                                .id(line.id)
                        }
                    }
                    .environment(\.locale, Locale(identifier: "de"))
                    .padding(20)
                    .background(Theme.card, in: RoundedRectangle(cornerRadius: 6))
                    .overlay(RoundedRectangle(cornerRadius: 6).stroke(Theme.line))
                    .shadow(color: Theme.ink.opacity(0.12), radius: 16, y: 8)
                    .padding()
                }
                .onAppear {
                    if let first = lines.first(where: { highlighted.contains($0.id) }) { proxy.scrollTo(first.id, anchor: .center) }
                    withAnimation(.easeOut(duration: 0.7).delay(0.35)) { marked = true }
                }
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
        VStack(alignment: mine ? .trailing : .leading, spacing: 4) {
            Text(message.text)
                .foregroundStyle(mine ? Theme.card : Theme.ink)
                .padding(.horizontal, 14).padding(.vertical, 10)
                .background(mine ? Theme.ink : Theme.paperDeep,
                            in: UnevenRoundedRectangle(topLeadingRadius: 16, bottomLeadingRadius: mine ? 16 : 4,
                                                       bottomTrailingRadius: mine ? 4 : 16, topTrailingRadius: 16))
            if let original = message.originalText {
                Text(original).font(.caption2).foregroundStyle(Theme.inkSoft).padding(.horizontal, 6)
            }
        }
        .frame(maxWidth: .infinity, alignment: mine ? .trailing : .leading)
        .padding(mine ? .leading : .trailing, 40)
        .transition(.move(edge: mine ? .trailing : .leading).combined(with: .opacity))
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
            Group {
                if let share = letter.activeShare {
                    conversation(share)
                } else {
                    shareForm
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

    private func conversation(_ share: ShareInfo) -> some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: 10) {
                    Label("Shared with \(share.tenantName)", systemImage: "person.2.fill")
                        .font(.footnote.weight(.semibold)).foregroundStyle(Theme.ok)
                        .padding(.horizontal, 12).padding(.vertical, 6)
                        .background(Theme.okBg, in: Capsule())
                        .padding(.bottom, 6)
                    if messages.isEmpty {
                        Text("No messages yet. Write to the counselling service below.")
                            .font(.subheadline).foregroundStyle(Theme.inkSoft).multilineTextAlignment(.center).padding(.top, 30)
                    }
                    ForEach(messages) { MessageBubble(message: $0).id($0.id) }
                    Button("Stop sharing", role: .destructive) {
                        Task { try? await model.api.revokeShare(id: share.id); dismiss() }
                    }
                    .font(.footnote.weight(.semibold)).foregroundStyle(Theme.danger).padding(.top, 24)
                }
                .padding()
                .animation(Motion.spring, value: messages.count)
            }
            .onChange(of: messages.count) { _, _ in
                if let last = messages.last { withAnimation { proxy.scrollTo(last.id, anchor: .bottom) } }
            }
            .safeAreaInset(edge: .bottom) {
                HStack(spacing: 8) {
                    TextField("Message", text: $text, axis: .vertical).lineLimit(1...4)
                        .padding(.leading, 16).padding(.vertical, 11)
                    Button {
                        Task {
                            if let sent = try? await model.api.sendMessage(shareId: share.id, text: text) {
                                messages.append(sent); text = ""
                            }
                        }
                    } label: {
                        Image(systemName: "arrow.up").font(.body.weight(.bold)).foregroundStyle(Theme.card)
                            .frame(width: 34, height: 34).background(Theme.ink, in: Circle())
                    }
                    .disabled(text.isEmpty).opacity(text.isEmpty ? 0.35 : 1)
                    .padding(.trailing, 5)
                    .accessibilityLabel("Send")
                }
                .background(Theme.card, in: RoundedRectangle(cornerRadius: 22))
                .overlay(RoundedRectangle(cornerRadius: 22).stroke(Theme.line))
                .padding()
                .sensoryFeedback(.success, trigger: messages.count)
            }
        }
    }

    private var shareForm: some View {
        Form {
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
                .tint(Theme.ok)
            } header: {
                VStack(alignment: .leading, spacing: 6) {
                    Image(systemName: "person.2.wave.2.fill").font(.title).foregroundStyle(Theme.ink)
                        .frame(width: 60, height: 60).background(Theme.highlighter.opacity(0.8), in: Circle())
                    Text("Free counselling services can check your individual case.")
                        .font(.subheadline).foregroundStyle(Theme.inkSoft).textCase(nil)
                }
                .padding(.bottom, 10)
            } footer: {
                Text("Consent version share-consent-v1.")
            }
            .listRowBackground(Theme.card)
            Section {
                Button {
                    Task {
                        guard let selected else { return }
                        do { _ = try await model.api.share(letterId: letter.id, tenantId: selected); dismiss() } catch {
                            model.error = error.localizedDescription
                        }
                    }
                } label: { Label("Share", systemImage: "paperplane.fill") }
                .buttonStyle(InkButtonStyle())
                .disabled(selected == nil || !consent)
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets())
            }
        }
    }
}
