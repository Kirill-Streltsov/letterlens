import LetterLensCore
import SwiftUI
import UIKit

/// Paper and ink, matching the web app (web/src/app/globals.css). Every screen has a full-bleed paper background.
enum Theme {
    static let paper = dynamic(light: 0xF4EEE2, dark: 0x14192B)
    static let paperDeep = dynamic(light: 0xEBE2CF, dark: 0x10142A)
    static let card = dynamic(light: 0xFFFDF8, dark: 0x1C2238)
    static let ink = dynamic(light: 0x1B2540, dark: 0xECE6D8)
    static let inkSoft = dynamic(light: 0x4B5472, dark: 0xB9B7C4)
    static let inkFaint = dynamic(light: 0x8A8FA3, dark: 0x8A8FA3)
    static let line = dynamic(light: 0xE2D8C3, dark: 0x2D3550)
    static let marker = dynamic(light: 0xFFE27A, dark: 0x6B5A12)
    static let markerSoft = dynamic(light: 0xFFF3C2, dark: 0x3A3417)
    static let ok = dynamic(light: 0x2F6B55, dark: 0x7FD1AD)
    static let okBg = dynamic(light: 0xE3F1EA, dark: 0x173329)
    static let check = dynamic(light: 0xB45A1F, dark: 0xF0A66D)
    static let checkBg = dynamic(light: 0xFBEADB, dark: 0x3B2616)
    static let link = dynamic(light: 0x2A4B98, dark: 0x9DB5FF)
    static let danger = dynamic(light: 0xA83434, dark: 0xFF9B9B)
    /// The bright highlighter yellow in both modes, for glows and the lens.
    static let highlighter = Color(UIColor(hex: 0xFFE27A))

    static func title(_ size: CGFloat = 28) -> Font { .system(size: size, weight: .semibold, design: .serif) }

    private static func dynamic(light: UInt32, dark: UInt32) -> Color {
        Color(UIColor { $0.userInterfaceStyle == .dark ? UIColor(hex: dark) : UIColor(hex: light) })
    }
}

enum Motion {
    static let spring = Animation.spring(response: 0.5, dampingFraction: 0.82)
    static let snappy = Animation.spring(response: 0.28, dampingFraction: 0.72)
    static let bouncy = Animation.spring(response: 0.45, dampingFraction: 0.6)
}

extension UIColor {
    convenience init(hex: UInt32) {
        self.init(red: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
                  blue: CGFloat(hex & 0xFF) / 255, alpha: 1)
    }
}

/// Paper with a darker wash in the top left and a faint highlighter glow in the top right, as on the web.
struct PaperBackground: ViewModifier {
    func body(content: Content) -> some View {
        content
            .scrollContentBackground(.hidden)
            .background {
                ZStack {
                    Theme.paper
                    RadialGradient(colors: [Theme.paperDeep, Theme.paperDeep.opacity(0)],
                                   center: UnitPoint(x: 0.05, y: -0.05), startRadius: 0, endRadius: 520)
                    RadialGradient(colors: [Theme.highlighter.opacity(0.22), Theme.highlighter.opacity(0)],
                                   center: UnitPoint(x: 1, y: 0), startRadius: 0, endRadius: 300)
                }
                .ignoresSafeArea()
            }
    }
}

struct CardStyle: ViewModifier {
    var padding: CGFloat = 16

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.card, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(Theme.line))
            .shadow(color: Theme.ink.opacity(0.04), radius: 0, y: 1)
            .shadow(color: Theme.ink.opacity(0.10), radius: 14, y: 8)
    }
}

/// Fades and lifts a view in once, after `delay`. Lists pass a small per-row delay for a cascade.
struct Rise: ViewModifier {
    var delay: Double = 0
    var distance: CGFloat = 16
    @State private var shown = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content
            .opacity(shown ? 1 : 0)
            .offset(y: shown || reduceMotion ? 0 : distance)
            .scaleEffect(shown || reduceMotion ? 1 : 0.98, anchor: .top)
            .onAppear {
                guard !shown else { return }
                withAnimation(reduceMotion ? .easeOut(duration: 0.2) : Motion.spring.delay(delay)) { shown = true }
            }
    }
}

extension View {
    func paperBackground() -> some View { modifier(PaperBackground()) }
    func card(padding: CGFloat = 16) -> some View { modifier(CardStyle(padding: padding)) }
    func rise(_ delay: Double = 0, distance: CGFloat = 16) -> some View { modifier(Rise(delay: delay, distance: distance)) }
    /// Cascade delay for the n-th item of a list, capped so long lists do not wait.
    func rise(index: Int, base: Double = 0) -> some View { rise(base + Double(min(index, 8)) * 0.06) }
}

func formatDate(_ iso: String?) -> String {
    guard let iso, let date = Deadlines.date(fromISO: iso) else { return "Date unknown" }
    return date.formatted(.dateTime.weekday(.abbreviated).day().month(.wide).year())
}

func formatMoney(_ value: String, _ currency: String) -> String {
    (Decimal(string: value) ?? 0).formatted(.currency(code: currency).locale(Locale(identifier: "de_DE")))
}
