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

