import LetterLensCore
import SwiftUI

struct SignInView: View {
    @Environment(AppModel.self) private var model
    @State private var busy = false

    private let points = [
        "Summaries in English, Turkish, Arabic, Ukrainian, Russian or plain German",
        "Dates and amounts are checked against the letter itself",
        "Text recognition runs on this iPhone; letters are deleted after 30 days",
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 30) {
                HStack(spacing: 10) {
                    LogoMark(size: 34)
                    Text("LetterLens").font(Theme.title(22).weight(.bold)).foregroundStyle(Theme.ink)
                }
                .rise(0)

                VStack(alignment: .leading, spacing: 2) {
                    Text("Official post,")
                    HStack(spacing: 0) {
                        Text("in ")
                        Text("plain words").markerSweep(delay: 0.7)
                        Text(".")
                    }
                }
                .font(Theme.title(40))
                .foregroundStyle(Theme.ink)
                .accessibilityElement(children: .combine)
                .accessibilityAddTraits(.isHeader)
                .rise(0.1)

                LetterDemo().padding(.horizontal, 4).rise(0.25)

                VStack(alignment: .leading, spacing: 14) {
                    ForEach(Array(points.enumerated()), id: \.offset) { index, point in
                        HStack(alignment: .firstTextBaseline, spacing: 12) {
                            Image(systemName: "checkmark")
                                .font(.caption.weight(.heavy)).foregroundStyle(Color(UIColor(hex: 0x1B2540)))
                                .frame(width: 22, height: 22)
                                .background(Theme.highlighter, in: Circle())
                                .alignmentGuide(.firstTextBaseline) { $0[VerticalAlignment.center] + 5 }
                            Text(point).foregroundStyle(Theme.inkSoft)
                        }
                        .rise(0.9 + Double(index) * 0.1)
                    }
                }
            }
            .padding(.horizontal, 24).padding(.top, 20).padding(.bottom, 12)
        }
        .scrollBounceBehavior(.basedOnSize)
        .safeAreaInset(edge: .bottom) {
            VStack(spacing: 10) {
                Button {
                    busy = true
                    Task { await model.signIn(); busy = false }
                } label: {
                    HStack(spacing: 10) {
                        if busy { ProgressView().tint(Theme.card) }
                        Text(model.config.usesDevAuth ? "Continue (local demo)" : "Sign in or create an account")
                    }
                }
                .buttonStyle(InkButtonStyle())
                .disabled(busy)
                .sensoryFeedback(.impact(weight: .light), trigger: busy) { _, new in new }
                Text("General information, not legal advice.").font(.footnote).foregroundStyle(Theme.inkFaint)
            }
            .padding(.horizontal, 24).padding(.top, 16).padding(.bottom, 8)
            .background {
                LinearGradient(colors: [Theme.paper.opacity(0), Theme.paper], startPoint: .top, endPoint: .init(x: 0.5, y: 0.35))
                    .ignoresSafeArea()
            }
            .rise(1.2)
        }
        .paperBackground()
    }
}

struct LettersView: View {
    @Environment(AppModel.self) private var model
    @State private var letters: [LetterListItem]?
    @State private var showNew = false

    /// The soonest deadline that has not passed, across all letters.
    private var nextUp: (LetterListItem, DeadlineSummary, Int)? {
        (letters ?? []).compactMap { letter -> (LetterListItem, DeadlineSummary, Int)? in
            guard let next = letter.nextDeadline, let iso = next.dueDate, let days = Deadlines.daysUntil(iso), days >= 0 else { return nil }
            return (letter, next, days)
        }
        .min { $0.2 < $1.2 }
    }

    /// Letters still being read; while there are any, the list refreshes itself.
    private var pending: [String] { (letters ?? []).filter { $0.status == .received || $0.status == .processing }.map(\.id) }

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 14) {
                if let letters {
                    if letters.isEmpty {
                        emptyState
                    } else {
                        if let up = nextUp {
                            NavigationLink(value: up.0.id) {
                                NextDeadlineCard(letter: up.0, deadline: up.1, days: up.2)
                            }
                            .buttonStyle(PressableStyle())
                            .rise(0)
                        }
                        if let me = model.me, let limit = me.lettersLimit { UsageCard(used: me.lettersThisMonth, limit: limit).rise(0.06) }
                        SectionTitle(text: "All letters", count: letters.count).rise(0.1)
                        ForEach(Array(letters.enumerated()), id: \.element.id) { index, letter in
                            NavigationLink(value: letter.id) { LetterRow(letter: letter) }
                                .buttonStyle(PressableStyle())
                                .rise(index: index, base: 0.12)
                                .transition(.asymmetric(insertion: .scale(scale: 0.92).combined(with: .opacity), removal: .opacity))
                        }
                    }
                } else {
                    ForEach(0..<4, id: \.self) { SkeletonRow().rise(index: $0) }
                }
            }
            .padding(.horizontal).padding(.top, 8).padding(.bottom, 90)
            .animation(Motion.spring, value: letters)
        }
        .paperBackground()
        .navigationTitle("My letters")
        .navigationDestination(for: String.self) { LetterDetailView(letterId: $0) }
        .safeAreaInset(edge: .bottom) {
            if letters?.isEmpty == false {
                Button { showNew = true } label: {
                    Label("Scan a letter", systemImage: "doc.viewfinder").padding(.horizontal, 6)
                }
                .buttonStyle(InkButtonStyle(fill: false))
                .padding(.bottom, 10)
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .sheet(isPresented: $showNew, onDismiss: { Task { await load() } }) {
            NavigationStack { NewLetterView() }
        }
        .refreshable { await load() }
        .task { await load() }
        .task(id: pending) {
            guard !pending.isEmpty else { return }
            try? await Task.sleep(for: .seconds(2))
            await load()
        }
    }

    private var emptyState: some View {
        VStack(spacing: 14) {
            EnvelopeArt(width: 230)
            Text("No letters yet").font(Theme.title(26)).foregroundStyle(Theme.ink)
            Text("Scan your first letter. LetterLens explains it in your language and finds the deadlines. It is deleted automatically after 30 days.")
                .multilineTextAlignment(.center).foregroundStyle(Theme.inkSoft)
            Button { showNew = true } label: { Label("Scan a letter", systemImage: "doc.viewfinder") }
                .buttonStyle(InkButtonStyle())
                .padding(.top, 6)
        }
        .padding(.vertical, 8)
        .card(padding: 22)
        .padding(.top, 16)
        .rise(0)
    }

    private func load() async {
        do { letters = try await model.api.letters() } catch { model.error = error.localizedDescription; letters = letters ?? [] }
    }
}

/// The soonest open deadline, in ink so it stands out from the paper cards.
struct NextDeadlineCard: View {
    let letter: LetterListItem
    let deadline: DeadlineSummary
    let days: Int

    var body: some View {
        HStack(alignment: .center, spacing: 16) {
            VStack(alignment: .leading, spacing: 6) {
                Label("Next deadline", systemImage: "bell.badge")
                    .font(.caption.weight(.semibold)).textCase(.uppercase).tracking(0.6)
                    .foregroundStyle(Theme.card.opacity(0.7))
                Text(formatDate(deadline.dueDate)).font(Theme.title(24)).foregroundStyle(Theme.card)
                Text(deadline.label.isEmpty ? (letter.headline ?? "Letter") : deadline.label)
                    .font(.subheadline).foregroundStyle(Theme.card.opacity(0.85)).lineLimit(2)
                    .multilineTextAlignment(.leading)
            }
            Spacer(minLength: 0)
            CountdownBadge(days: days)
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background {
            RoundedRectangle(cornerRadius: 20, style: .continuous).fill(Theme.ink)
                .overlay(alignment: .topTrailing) {
                    Circle().fill(Theme.highlighter.opacity(0.25)).frame(width: 160).blur(radius: 30).offset(x: 50, y: -60)
                }
                .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        }
        .shadow(color: Theme.ink.opacity(0.3), radius: 18, y: 10)
        .accessibilityElement(children: .combine)
        .accessibilityHint("Opens the letter")
    }
}

/// Days left, in a highlighter circle that fills up as the date comes closer.
struct CountdownBadge: View {
    let days: Int
    @State private var shown = 0.0

    var body: some View {
        ZStack {
            Circle().stroke(Theme.card.opacity(0.15), lineWidth: 6)
            Circle().trim(from: 0, to: shown).stroke(Theme.highlighter, style: StrokeStyle(lineWidth: 6, lineCap: .round))
                .rotationEffect(.degrees(-90))
            VStack(spacing: -2) {
                Text(days == 0 ? "!" : "\(days)").font(Theme.title(26).weight(.bold)).contentTransition(.numericText())
                Text(days == 0 ? "today" : days == 1 ? "day" : "days").font(.caption2.weight(.semibold))
            }
            .foregroundStyle(Theme.card)
        }
        .frame(width: 76, height: 76)
        .onAppear {
            // A 30-day window: a full ring means the deadline is today.
            withAnimation(.easeOut(duration: 1.1).delay(0.3)) { shown = max(0.06, 1 - Double(min(days, 30)) / 30) }
        }
    }
}

struct UsageCard: View {
    let used: Int
    let limit: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Free plan").font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink)
                Spacer()
                Text("\(max(limit - used, 0)) of \(limit) letters left this month")
                    .font(.footnote).foregroundStyle(Theme.inkSoft)
            }
            ProgressBar(value: Double(used) / Double(max(limit, 1)), tint: used >= limit ? Theme.check : Theme.ink)
        }
        .card(padding: 14)
        .accessibilityElement(children: .combine)
    }
}

struct LetterRow: View {
    let letter: LetterListItem

    private var deadlinePill: Pill? {
        letter.nextDeadline.flatMap { Pill.deadline(iso: $0.dueDate, status: $0.status) }
    }

    var body: some View {
        HStack(alignment: .center, spacing: 14) {
            TypeBadge(letterType: letter.letterType)
                .frame(maxHeight: .infinity, alignment: .top)
            VStack(alignment: .leading, spacing: 5) {
                Text(letter.headline ?? letter.sender ?? "Reading the letter…")
                    .font(.system(.headline, design: .serif)).foregroundStyle(Theme.ink).lineLimit(2)
                    .multilineTextAlignment(.leading)
                HStack(spacing: 4) {
                    Text(LetterTypes.names[letter.letterType ?? "other"] ?? "Letter")
                    Text("·")
                    Text(letter.createdAt, format: .relative(presentation: .named))
                }
                .font(.caption).foregroundStyle(Theme.inkSoft).lineLimit(1)
                if letter.status != .ready || letter.shared || deadlinePill != nil {
                    ViewThatFits(in: .horizontal) {
                        HStack(spacing: 6) { pills(withDate: true) }
                        HStack(spacing: 6) { pills(withDate: false) }
                        VStack(alignment: .leading, spacing: 6) { pills(withDate: false) }
                    }
                    .padding(.top, 3)
                }
            }
            Spacer(minLength: 0)
            Image(systemName: "chevron.right").font(.footnote.weight(.semibold)).foregroundStyle(Theme.inkFaint)
        }
        .card()
        .accessibilityElement(children: .combine)
    }

    @ViewBuilder
    private func pills(withDate: Bool) -> some View {
        switch letter.status {
        case .received, .processing:
            HStack(spacing: 5) {
                ProgressView().controlSize(.mini).tint(Theme.check)
                Text("Reading…")
            }
            .font(.caption.weight(.semibold)).foregroundStyle(Theme.check)
            .padding(.horizontal, 10).padding(.vertical, 4)
            .background(Theme.checkBg, in: Capsule())
        case .failed: Pill(text: "failed", kind: .check, icon: "exclamationmark.triangle")
        case .ready: EmptyView()
        }
        if let deadlinePill {
            deadlinePill
            if withDate, let iso = letter.nextDeadline?.dueDate, let date = Deadlines.date(fromISO: iso) {
                Text(date.formatted(.dateTime.day().month(.abbreviated).year())).font(.caption2).foregroundStyle(Theme.inkSoft)
                    .fixedSize()
            }
        }
        if letter.shared { Pill(text: "shared", kind: .ok, icon: "person.2") }
    }
}
