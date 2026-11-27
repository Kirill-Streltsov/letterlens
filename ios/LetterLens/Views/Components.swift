import LetterLensCore
import SwiftUI

// MARK: - Buttons

/// The web's `.btn`: an ink capsule (or an outlined "ghost" one) that sinks a little when pressed.
struct InkButtonStyle: ButtonStyle {
    enum Kind { case primary, ghost, danger }
    var kind: Kind = .primary
    var fill = true
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        let pressed = configuration.isPressed
        configuration.label
            .font(.headline)
            .padding(.horizontal, 22).padding(.vertical, 15)
            .frame(maxWidth: fill ? .infinity : nil)
            .foregroundStyle(foreground)
            .background { Capsule().fill(kind == .primary ? Theme.ink : Theme.card.opacity(0.6)) }
            .overlay { if kind != .primary { Capsule().stroke(foreground, lineWidth: 1.5) } }
            .shadow(color: Theme.ink.opacity(kind == .primary ? (pressed ? 0.12 : 0.28) : 0),
                    radius: pressed ? 4 : 14, y: pressed ? 2 : 8)
            .scaleEffect(pressed ? 0.965 : 1)
            .opacity(isEnabled ? 1 : 0.45)
            .animation(Motion.snappy, value: pressed)
            .contentShape(Capsule())
    }

    private var foreground: Color {
        switch kind {
        case .primary: Theme.card
        case .ghost: Theme.ink
        case .danger: Theme.danger
        }
    }
}

/// Small paper-coloured capsule for secondary actions inside cards.
struct ChipButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(Theme.ink)
            .padding(.horizontal, 14).padding(.vertical, 9)
            .background(configuration.isPressed ? Theme.markerSoft : Theme.paperDeep, in: Capsule())
            .overlay(Capsule().stroke(Theme.line))
            .scaleEffect(configuration.isPressed ? 0.95 : 1)
            .animation(Motion.snappy, value: configuration.isPressed)
    }
}

/// For whole cards that act as buttons or links: a gentle press-in.
struct PressableStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.975 : 1)
            .brightness(configuration.isPressed ? -0.015 : 0)
            .animation(Motion.snappy, value: configuration.isPressed)
    }
}

// MARK: - Pills

struct Pill: View {
    enum Kind { case neutral, ok, check, urgent }
    let text: String
    var kind: Kind = .neutral
    var icon: String?
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        HStack(spacing: 4) {
            if let icon { Image(systemName: icon).font(.caption2.weight(.bold)) }
            Text(text)
        }
        .font(.caption.weight(.semibold))
        .lineLimit(1)
        .fixedSize()
        .padding(.horizontal, 10).padding(.vertical, 4)
        .foregroundStyle(foreground)
        .background(background, in: Capsule())
        .phaseAnimator(kind == .urgent && !reduceMotion ? [false, true] : [false]) { view, on in
            view.shadow(color: Color(UIColor(hex: 0xA83434)).opacity(on ? 0.55 : 0), radius: on ? 6 : 0)
        } animation: { _ in .easeInOut(duration: 1.1) }
    }

    private var foreground: Color {
        switch kind {
        case .neutral: Theme.inkSoft
        case .ok: Theme.ok
        case .check: Theme.check
        case .urgent: .white
        }
    }

    private var background: Color {
        switch kind {
        case .neutral: Theme.paperDeep
        case .ok: Theme.okBg
        case .check: Theme.checkBg
        case .urgent: Color(UIColor(hex: 0xA83434))
        }
    }

    static func deadline(iso: String?, status: String) -> Pill? {
        guard let iso, let days = Deadlines.daysUntil(iso) else { return nil }
        let label = Deadlines.relativeLabel(days: days)
        switch Deadlines.urgency(days: days) {
        case .past: return Pill(text: label, icon: "clock.badge.checkmark")
        case .urgent: return Pill(text: label, kind: .urgent, icon: "exclamationmark")
        default: return Pill(text: label, kind: status == "verified" ? .ok : .check, icon: "clock")
        }
    }
}

// MARK: - Small pieces

/// Words with a highlighter stroke drawn under them from left to right, like `<mark>` on the web.
struct MarkerSweep: ViewModifier {
    var delay: Double = 0.4
    var duration: Double = 0.8
    /// Full height marks a whole line (as on a letter); otherwise only the lower half, like `<mark>` on the web.
    var fullHeight = false
    @State private var progress: CGFloat = 0
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content
            .background(alignment: .bottomLeading) {
                GeometryReader { geo in
                    RoundedRectangle(cornerRadius: 3)
                        .fill(Theme.marker)
                        .frame(width: (geo.size.width + 6) * progress, height: geo.size.height * (fullHeight ? 1 : 0.48))
                        .offset(x: -3, y: fullHeight ? 0 : geo.size.height * 0.5)
                }
            }
            .onAppear {
                if reduceMotion { progress = 1; return }
                withAnimation(.easeOut(duration: duration).delay(delay)) { progress = 1 }
            }
    }
}

extension View {
    func markerSweep(delay: Double = 0.4, fullHeight: Bool = false) -> some View {
        modifier(MarkerSweep(delay: delay, fullHeight: fullHeight))
    }
}

/// The SF Symbol for a letter type, on a highlighter disc.
struct TypeBadge: View {
    let letterType: String?
    var size: CGFloat = 42

    var body: some View {
        Image(systemName: LetterTypes.symbols[letterType ?? "other"] ?? "envelope")
            .font(.system(size: size * 0.42, weight: .semibold))
            .foregroundStyle(Theme.ink)
            .frame(width: size, height: size)
            .background(Theme.marker.opacity(0.85), in: Circle())
            .overlay(Circle().stroke(Theme.ink.opacity(0.08)))
    }
}

/// A section title in the serif face with an optional count.
struct SectionTitle: View {
    let text: String
    var count: Int?
    var icon: String?

    var body: some View {
        HStack(spacing: 8) {
            if let icon { Image(systemName: icon).font(.headline).foregroundStyle(Theme.inkSoft) }
            Text(text).font(Theme.title(21)).foregroundStyle(Theme.ink)
            if let count {
                Text("\(count)").font(.caption.weight(.bold)).foregroundStyle(Theme.inkSoft)
                    .padding(.horizontal, 7).padding(.vertical, 2)
                    .background(Theme.paperDeep, in: Capsule())
            }
            Spacer()
        }
        .padding(.top, 6)
        .accessibilityAddTraits(.isHeader)
    }
}

struct ProgressBar: View {
    let value: Double
    var tint: Color = Theme.ink
    @State private var shown = 0.0

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Capsule().fill(Theme.paperDeep)
                Capsule().fill(tint).frame(width: max(geo.size.height, geo.size.width * shown))
            }
        }
        .frame(height: 8)
        .onAppear { withAnimation(Motion.spring.delay(0.2)) { shown = min(max(value, 0), 1) } }
        .onChange(of: value) { _, new in withAnimation(Motion.spring) { shown = min(max(new, 0), 1) } }
        .accessibilityHidden(true)
    }
}

/// A shimmering placeholder, like `.skeleton` on the web.
struct Shimmer: ViewModifier {
    @State private var phase: CGFloat = 0
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content
            .overlay {
                GeometryReader { geo in
                    LinearGradient(colors: [Theme.card.opacity(0), Theme.card.opacity(0.75), Theme.card.opacity(0)],
                                   startPoint: .leading, endPoint: .trailing)
                        .frame(width: geo.size.width * 0.5)
                        .offset(x: -geo.size.width * 0.5 + phase * geo.size.width * 1.5)
                }
                .mask(content)
                .opacity(reduceMotion ? 0 : 1)
            }
            .onAppear {
                withAnimation(.linear(duration: 1.3).repeatForever(autoreverses: false)) { phase = 1 }
            }
    }
}

extension View {
    func shimmer() -> some View { modifier(Shimmer()) }
}

struct SkeletonBar: View {
    var width: CGFloat? = nil
    var height: CGFloat = 12
    var body: some View {
        RoundedRectangle(cornerRadius: height / 2).fill(Theme.paperDeep).frame(width: width, height: height)
    }
}

struct SkeletonRow: View {
    var body: some View {
        HStack(spacing: 14) {
            Circle().fill(Theme.paperDeep).frame(width: 42, height: 42)
            VStack(alignment: .leading, spacing: 9) {
                SkeletonBar(height: 14).frame(maxWidth: .infinity)
                SkeletonBar(width: 120, height: 10)
            }
            SkeletonBar(width: 64, height: 22)
        }
        .shimmer()
        .card()
        .accessibilityLabel("Loading")
    }
}

/// A short message that slides up from the bottom of the screen.
struct Toast: Equatable {
    var text: String
    var icon: String = "checkmark.circle.fill"
    var isError = false
}

struct ToastModifier: ViewModifier {
    @Binding var toast: Toast?

    func body(content: Content) -> some View {
        content
            .overlay(alignment: .bottom) {
                if let toast {
                    HStack(spacing: 10) {
                        Image(systemName: toast.icon).font(.headline)
                            .foregroundStyle(toast.isError ? Theme.danger : Theme.ok)
                            .symbolEffect(.bounce, value: toast.text)
                        Text(toast.text).font(.subheadline.weight(.medium)).foregroundStyle(Theme.ink)
                    }
                    .padding(.horizontal, 18).padding(.vertical, 13)
                    .background(Theme.card, in: Capsule())
                    .overlay(Capsule().stroke(Theme.line))
                    .shadow(color: Theme.ink.opacity(0.18), radius: 18, y: 10)
                    .padding(.horizontal, 24).padding(.bottom, 24)
                    .transition(.move(edge: .bottom).combined(with: .opacity).combined(with: .scale(scale: 0.9)))
                    .id(toast.text)
                    .task(id: toast.text) {
                        try? await Task.sleep(for: .seconds(2.6))
                        withAnimation(Motion.spring) { self.toast = nil }
                    }
                    .accessibilityAddTraits(.isStaticText)
                }
            }
            .animation(Motion.bouncy, value: toast)
            .sensoryFeedback(trigger: toast) { _, new in
                guard let new else { return nil }
                return new.isError ? .error : .success
            }
    }
}

extension View {
    func toast(_ toast: Binding<Toast?>) -> some View { modifier(ToastModifier(toast: toast)) }
}
