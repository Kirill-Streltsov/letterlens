import LetterLensCore
import SwiftUI
import UIKit

/// Paper and ink, matching the web app. Every screen has a full-bleed paper background.
enum Theme {
    static let paper = dynamic(light: 0xF4EEE2, dark: 0x14192B)
    static let paperDeep = dynamic(light: 0xEBE2CF, dark: 0x10142A)
    static let card = dynamic(light: 0xFFFDF8, dark: 0x1C2238)
    static let ink = dynamic(light: 0x1B2540, dark: 0xECE6D8)
    static let inkSoft = dynamic(light: 0x4B5472, dark: 0xB9B7C4)
    static let line = dynamic(light: 0xE2D8C3, dark: 0x2D3550)
    static let marker = dynamic(light: 0xFFE27A, dark: 0x6B5A12)
    static let ok = dynamic(light: 0x2F6B55, dark: 0x7FD1AD)
    static let check = dynamic(light: 0xB45A1F, dark: 0xF0A66D)
    static let danger = Color(red: 0.66, green: 0.20, blue: 0.20)

    static func title(_ size: CGFloat = 28) -> Font { .system(size: size, weight: .semibold, design: .serif) }

    private static func dynamic(light: UInt32, dark: UInt32) -> Color {
        Color(UIColor { $0.userInterfaceStyle == .dark ? UIColor(hex: dark) : UIColor(hex: light) })
    }
}

extension UIColor {
    convenience init(hex: UInt32) {
        self.init(red: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
                  blue: CGFloat(hex & 0xFF) / 255, alpha: 1)
    }
}

struct PaperBackground: ViewModifier {
    func body(content: Content) -> some View {
        content
            .scrollContentBackground(.hidden)
            .background(
                LinearGradient(colors: [Theme.paperDeep, Theme.paper], startPoint: .top, endPoint: .center)
                    .ignoresSafeArea()
            )
    }
}

struct CardStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.card, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).stroke(Theme.line))
            .shadow(color: Theme.ink.opacity(0.08), radius: 10, y: 4)
    }
}

extension View {
    func paperBackground() -> some View { modifier(PaperBackground()) }
    func card() -> some View { modifier(CardStyle()) }
}

struct Pill: View {
    enum Kind { case neutral, ok, check, urgent }
    let text: String
    var kind: Kind = .neutral

    var body: some View {
        Text(text)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 10).padding(.vertical, 3)
            .foregroundStyle(foreground)
            .background(background, in: Capsule())
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
        case .ok: Theme.ok.opacity(0.14)
        case .check: Theme.check.opacity(0.16)
        case .urgent: Theme.danger
        }
    }

    static func deadline(iso: String?, status: String) -> Pill? {
        guard let iso, let days = Deadlines.daysUntil(iso) else { return nil }
        let label = Deadlines.relativeLabel(days: days)
        switch Deadlines.urgency(days: days) {
        case .past: return Pill(text: label)
        case .urgent: return Pill(text: label, kind: .urgent)
        default: return Pill(text: label, kind: status == "verified" ? .ok : .check)
        }
    }
}

