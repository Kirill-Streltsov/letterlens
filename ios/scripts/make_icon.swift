// Draws the 1024 px app icons: a letter rising out of an envelope, read through a highlighter-yellow lens.
// Writes the light, dark and tinted variants (iOS 18+ picks one to match the home screen).
// Usage: swift scripts/make_icon.swift LetterLens/Resources/Assets.xcassets/AppIcon.appiconset
//
// Every shape is closed and joined with round joins, so no white fill shows outside an outline.
// The images are opaque RGB (no alpha channel), as App Store Connect requires.
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

struct Palette {
    var backgroundTop: UInt32, backgroundBottom: UInt32, glow: UInt32, glowAlpha: CGFloat
    var outline: UInt32, ink: UInt32, envelopeBack: UInt32, envelopeFront: UInt32, sheet: UInt32, textBar: UInt32
    var marker: UInt32, lensGlare: CGFloat
}

let light = Palette(backgroundTop: 0xF7F2E8, backgroundBottom: 0xE9DEC8, glow: 0xFFE27A, glowAlpha: 0.55,
                    outline: 0x1B2540, ink: 0x1B2540, envelopeBack: 0xE4D8BF, envelopeFront: 0xFFFDF8, sheet: 0xFFFFFF, textBar: 0xD9CFBC,
                    marker: 0xFFE27A, lensGlare: 0.75)
let dark = Palette(backgroundTop: 0x1E2540, backgroundBottom: 0x0E1224, glow: 0xFFE27A, glowAlpha: 0.16,
                   outline: 0xECE6D8, ink: 0x1B2540, envelopeBack: 0x3A4262, envelopeFront: 0x283050, sheet: 0xFFFDF8,
                   textBar: 0xCFC6B4,
                   marker: 0xFFD84D, lensGlare: 0.6)
let tinted = Palette(backgroundTop: 0x000000, backgroundBottom: 0x000000, glow: 0xFFFFFF, glowAlpha: 0,
                     outline: 0xFFFFFF, ink: 0x1A1A1A, envelopeBack: 0x3C3C3C, envelopeFront: 0x6E6E6E, sheet: 0xD0D0D0,
                     textBar: 0x9A9A9A,
                     marker: 0xFFFFFF, lensGlare: 0)

func color(_ hex: UInt32, _ alpha: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
}

func roundedRect(_ rect: CGRect, _ radius: CGFloat) -> CGPath {
    CGPath(roundedRect: rect, cornerWidth: radius, cornerHeight: radius, transform: nil)
}

func draw(_ p: Palette, in ctx: CGContext) {
    let size: CGFloat = 1024
    let stroke: CGFloat = 30
    defer { ctx.restoreGState() }
    ctx.setLineJoin(.round)
    ctx.setLineCap(.round)

    // Paper background with a soft highlighter glow in the top right (as on the web sign-in panel).
    let space = CGColorSpace(name: CGColorSpace.sRGB)!
    let bg = CGGradient(colorsSpace: space, colors: [color(p.backgroundTop), color(p.backgroundBottom)] as CFArray,
                        locations: [0, 1])!
    ctx.drawLinearGradient(bg, start: CGPoint(x: 0, y: size), end: CGPoint(x: 0, y: 0), options: [])
    let glow = CGGradient(colorsSpace: space, colors: [color(p.glow, p.glowAlpha), color(p.glow, 0)] as CFArray,
                          locations: [0, 1])!
    ctx.drawRadialGradient(glow, startCenter: CGPoint(x: 800, y: 860), startRadius: 0,
                           endCenter: CGPoint(x: 800, y: 860), endRadius: 520, options: [])

    // Artwork sits a little low and left of centre so the lens handle balances it.
    ctx.saveGState()
    ctx.translateBy(x: -6, y: -22)

    // Envelope geometry (CoreGraphics: origin bottom left).
    let env = CGRect(x: 122, y: 226, width: 620, height: 430)
    let radius: CGFloat = 46
    let vDepth: CGFloat = 230  // how far the front pocket's V dips below the top edge

    // 1. Envelope back.
    let back = roundedRect(env, radius)
    ctx.addPath(back); ctx.setFillColor(color(p.envelopeBack)); ctx.fillPath()
    ctx.addPath(back); ctx.setStrokeColor(color(p.outline)); ctx.setLineWidth(stroke); ctx.strokePath()

    // 2. The letter, tilted, rising out of the envelope.
    ctx.saveGState()
    ctx.translateBy(x: env.midX, y: env.maxY)
    ctx.rotate(by: 5 * .pi / 180)
    let sheet = CGRect(x: -235, y: -260, width: 450, height: 470)
    let sheetPath = roundedRect(sheet, 26)
    ctx.addPath(sheetPath); ctx.setFillColor(color(p.sheet)); ctx.fillPath()
    ctx.addPath(sheetPath); ctx.setStrokeColor(color(p.outline)); ctx.setLineWidth(stroke * 0.8); ctx.strokePath()
    // Text: a marked line between plain ones.
    func bar(_ y: CGFloat, _ width: CGFloat, _ fill: CGColor, height: CGFloat = 24) {
        ctx.addPath(roundedRect(CGRect(x: sheet.minX + 56, y: y, width: width, height: height), height / 2))
        ctx.setFillColor(fill); ctx.fillPath()
    }
    bar(sheet.maxY - 96, 210, color(p.ink, 0.85), height: 30)
    bar(sheet.maxY - 160, 330, color(p.textBar))
    ctx.addPath(roundedRect(CGRect(x: sheet.minX + 40, y: sheet.maxY - 238, width: 360, height: 52), 14))
    ctx.setFillColor(color(p.marker)); ctx.fillPath()
    bar(sheet.maxY - 224, 260, color(p.ink, 0.8))
    bar(sheet.maxY - 296, 300, color(p.textBar))
    ctx.restoreGState()

    // 3. Front pocket: sides and bottom of the envelope, with a V cut into the top.
    let front = CGMutablePath()
    // Start where the back's rounded corner meets its side, so the outlines continue into each other.
    front.move(to: CGPoint(x: env.minX, y: env.maxY - radius))
    front.addLine(to: CGPoint(x: env.midX, y: env.maxY - vDepth))
    front.addLine(to: CGPoint(x: env.maxX, y: env.maxY - radius))
    front.addArc(tangent1End: CGPoint(x: env.maxX, y: env.minY), tangent2End: CGPoint(x: env.minX, y: env.minY), radius: radius)
    front.addArc(tangent1End: CGPoint(x: env.minX, y: env.minY), tangent2End: CGPoint(x: env.minX, y: env.maxY), radius: radius)
    front.closeSubpath()
    ctx.addPath(front); ctx.setFillColor(color(p.envelopeFront)); ctx.fillPath()
    ctx.addPath(front); ctx.setStrokeColor(color(p.outline)); ctx.setLineWidth(stroke); ctx.strokePath()

    // 4. The lens: handle first, then an opaque glass so nothing shows through it.
    let lensCenter = CGPoint(x: 690, y: 330)
    let lensRadius: CGFloat = 168
    ctx.setStrokeColor(color(p.outline))
    ctx.setLineWidth(70)
    ctx.move(to: CGPoint(x: lensCenter.x + 140, y: lensCenter.y - 140))
    ctx.addLine(to: CGPoint(x: 905, y: 116))
    ctx.strokePath()
    let lensRect = CGRect(x: lensCenter.x - lensRadius, y: lensCenter.y - lensRadius, width: lensRadius * 2, height: lensRadius * 2)
    ctx.addEllipse(in: lensRect); ctx.setFillColor(color(p.marker)); ctx.fillPath()
    // Magnified text inside the lens.
    ctx.saveGState()
    ctx.addEllipse(in: lensRect.insetBy(dx: 6, dy: 6)); ctx.clip()
    ctx.setStrokeColor(color(p.ink, 0.88)); ctx.setLineWidth(30)
    ctx.move(to: CGPoint(x: lensCenter.x - 92, y: lensCenter.y + 42)); ctx.addLine(to: CGPoint(x: lensCenter.x + 96, y: lensCenter.y + 42))
    ctx.move(to: CGPoint(x: lensCenter.x - 92, y: lensCenter.y - 34)); ctx.addLine(to: CGPoint(x: lensCenter.x + 40, y: lensCenter.y - 34))
    ctx.strokePath()
    ctx.restoreGState()
    // Glare.
    if p.lensGlare > 0 {
        ctx.setStrokeColor(color(0xFFFFFF, p.lensGlare)); ctx.setLineWidth(18)
        ctx.addArc(center: lensCenter, radius: lensRadius - 40, startAngle: 2.05, endAngle: 2.75, clockwise: false)
        ctx.strokePath()
    }
    ctx.addEllipse(in: lensRect); ctx.setStrokeColor(color(p.outline)); ctx.setLineWidth(34); ctx.strokePath()
}

func write(_ palette: Palette, to url: URL) {
    let ctx = CGContext(data: nil, width: 1024, height: 1024, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    draw(palette, in: ctx)
    let dest = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
    guard CGImageDestinationFinalize(dest) else { fatalError("could not write \(url.path)") }
}

let dir = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ".")
write(light, to: dir.appendingPathComponent("icon-1024.png"))
write(dark, to: dir.appendingPathComponent("icon-dark-1024.png"))
write(tinted, to: dir.appendingPathComponent("icon-tinted-1024.png"))
print("Wrote icons to \(dir.path)")
