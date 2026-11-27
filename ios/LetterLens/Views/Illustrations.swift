import SwiftUI
import UIKit

// Brand drawings, matching web/src/components/Brand.tsx and the app icon (scripts/make_icon.swift).
// They are drawn in Canvas so every stroke meets its outline cleanly at any size and in both colour schemes.

private func clamp01(_ x: Double) -> Double { min(max(x, 0), 1) }
private func easeOut(_ x: Double) -> Double { let t = clamp01(x); return 1 - pow(1 - t, 3) }
private func easeOutBack(_ x: Double) -> Double {
    let t = clamp01(x), c1 = 1.70158, c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)
}

/// Front pocket of an open envelope: sides and bottom with a V cut into the top.
/// It starts where the rounded top corners end, so its outline continues the back's outline.
private func pocketPath(_ r: CGRect, radius: CGFloat, depth: CGFloat) -> Path {
    var p = Path()
    p.move(to: CGPoint(x: r.minX, y: r.minY + radius))
    p.addLine(to: CGPoint(x: r.midX, y: r.minY + depth))
    p.addLine(to: CGPoint(x: r.maxX, y: r.minY + radius))
    p.addArc(tangent1End: CGPoint(x: r.maxX, y: r.maxY), tangent2End: CGPoint(x: r.minX, y: r.maxY), radius: radius)
    p.addArc(tangent1End: CGPoint(x: r.minX, y: r.maxY), tangent2End: CGPoint(x: r.minX, y: r.minY), radius: radius)
    p.closeSubpath()
    return p
}

private func drawLens(_ ctx: GraphicsContext, center c: CGPoint, radius r: CGFloat, line: CGFloat, glare: Bool = true) {
    let round = StrokeStyle(lineWidth: line * 2, lineCap: .round)
    var handle = Path()
    handle.move(to: CGPoint(x: c.x + r * 0.72, y: c.y + r * 0.72))
    handle.addLine(to: CGPoint(x: c.x + r * 1.45, y: c.y + r * 1.45))
    ctx.stroke(handle, with: .color(Theme.ink), style: round)
    let disc = Path(ellipseIn: CGRect(x: c.x - r, y: c.y - r, width: r * 2, height: r * 2))
    ctx.fill(disc, with: .color(Theme.highlighter))
    var inner = ctx
    inner.clip(to: disc)
    var text = Path()
    text.move(to: CGPoint(x: c.x - r * 0.55, y: c.y - r * 0.22)); text.addLine(to: CGPoint(x: c.x + r * 0.58, y: c.y - r * 0.22))
    text.move(to: CGPoint(x: c.x - r * 0.55, y: c.y + r * 0.24)); text.addLine(to: CGPoint(x: c.x + r * 0.22, y: c.y + r * 0.24))
    inner.stroke(text, with: .color(Color(UIColor(hex: 0x1B2540)).opacity(0.85)), style: StrokeStyle(lineWidth: r * 0.18, lineCap: .round))
    if glare {
        var arc = Path()
        arc.addArc(center: c, radius: r * 0.72, startAngle: .degrees(200), endAngle: .degrees(240), clockwise: false)
        inner.stroke(arc, with: .color(.white.opacity(0.75)), style: StrokeStyle(lineWidth: r * 0.11, lineCap: .round))
    }
    ctx.stroke(disc, with: .color(Theme.ink), lineWidth: line)
}

/// The small logo: envelope and lens.
struct LogoMark: View {
    var size: CGFloat = 30

    var body: some View {
        Canvas { ctx, sz in
            let s = sz.width / 48
            let body = CGRect(x: 4 * s, y: 10 * s, width: 32 * s, height: 24 * s)
            let shape = Path(roundedRect: body, cornerRadius: 3.5 * s, style: .continuous)
            ctx.fill(shape, with: .color(Theme.card))
            var flap = ctx
            flap.clip(to: shape)
            var v = Path()
            v.move(to: CGPoint(x: body.minX, y: body.minY)); v.addLine(to: CGPoint(x: body.midX, y: 23 * s))
            v.addLine(to: CGPoint(x: body.maxX, y: body.minY))
            flap.stroke(v, with: .color(Theme.ink), style: StrokeStyle(lineWidth: 2.5 * s, lineJoin: .round))
            ctx.stroke(shape, with: .color(Theme.ink), lineWidth: 2.5 * s)
            drawLens(ctx, center: CGPoint(x: 32 * s, y: 30 * s), radius: 8.5 * s, line: 2.5 * s, glare: false)
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

/// Envelope, a letter rising out of it with one marked line, and a lens that drifts over it.
/// The brand illustration for the sign-in screen and empty states.
struct EnvelopeArt: View {
    var width: CGFloat = 240
    @State private var start = Date()
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        TimelineView(.animation(minimumInterval: 1 / 60, paused: reduceMotion)) { timeline in
            let t = reduceMotion ? 10 : timeline.date.timeIntervalSince(start)
            Canvas { ctx, size in
                ctx.scaleBy(x: size.width / 240, y: size.width / 240)
                draw(ctx, t: t)
            }
        }
        .frame(width: width, height: width * 190 / 240)
        .onAppear { start = Date() }
        .accessibilityHidden(true)
    }

    private func draw(_ ctx: GraphicsContext, t: Double) {
        let ink = Theme.ink
        let env = CGRect(x: 20, y: 72, width: 172, height: 104)
        let radius: CGFloat = 14
        let rise = easeOutBack((t - 0.15) / 0.8)
        let sweep = easeOut((t - 0.95) / 0.6)
        let lensIn = easeOutBack((t - 0.55) / 0.7)

        // Shadow on the paper.
        ctx.fill(Path(ellipseIn: CGRect(x: 30, y: 172, width: 170, height: 14)), with: .color(ink.opacity(0.07)))

        // Back.
        let back = Path(roundedRect: env, cornerRadius: radius, style: .circular)
        ctx.fill(back, with: .color(Theme.paperDeep))
        ctx.stroke(back, with: .color(ink), lineWidth: 4)

        // Letter.
        var sheet = ctx
        sheet.translateBy(x: env.midX, y: env.minY + (1 - rise) * 70)
        sheet.rotate(by: .degrees(-5))
        let page = CGRect(x: -58, y: -62, width: 116, height: 112)
        let pageShape = Path(roundedRect: page, cornerRadius: 8)
        sheet.fill(pageShape, with: .color(Theme.card))
        sheet.stroke(pageShape, with: .color(ink), lineWidth: 3)
        func bar(_ y: CGFloat, _ w: CGFloat, _ color: Color, h: CGFloat = 5) {
            sheet.fill(Path(roundedRect: CGRect(x: page.minX + 14, y: y, width: w, height: h), cornerRadius: h / 2), with: .color(color))
        }
        bar(-50, 44, ink.opacity(0.85), h: 7)
        bar(-36, 82, Theme.line)
        sheet.fill(Path(roundedRect: CGRect(x: page.minX + 10, y: -26, width: 94 * sweep, height: 13), cornerRadius: 4),
                   with: .color(Theme.highlighter))
        bar(-22, 66, ink.opacity(0.7))
        bar(-8, 76, Theme.line)

        // Front pocket.
        let front = pocketPath(env, radius: radius, depth: 58)
        ctx.fill(front, with: .color(Theme.card))
        ctx.stroke(front, with: .color(ink), style: StrokeStyle(lineWidth: 4, lineJoin: .round))

        // Lens, drifting gently once it has arrived.
        let drift = reduceMotion ? 0 : max(t - 1.3, 0)
        let center = CGPoint(x: 172 + sin(drift * 0.9) * 5, y: 128 + cos(drift * 1.3) * 3.5)
        var lens = ctx
        lens.translateBy(x: center.x, y: center.y)
        lens.scaleBy(x: lensIn, y: lensIn)
        lens.rotate(by: .degrees(sin(drift * 0.7) * 4))
        drawLens(lens, center: .zero, radius: 28, line: 4)
    }
}

/// A sheet whose lines are read one after another by a lens: shown while a letter is processed.
struct ReadingArt: View {
    var width: CGFloat = 220
    @State private var start = Date()
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let rows: [CGFloat] = [0.86, 0.7, 0.92, 0.55, 0.8]

    var body: some View {
        TimelineView(.animation(minimumInterval: 1 / 60, paused: reduceMotion)) { timeline in
            let t = reduceMotion ? 0.7 : timeline.date.timeIntervalSince(start)
            Canvas { ctx, size in
                ctx.scaleBy(x: size.width / 220, y: size.width / 220)
                draw(ctx, t: t)
            }
        }
        .frame(width: width, height: width * 150 / 220)
        .onAppear { start = Date() }
        .accessibilityHidden(true)
    }

    private func draw(_ ctx: GraphicsContext, t: Double) {
        let page = CGRect(x: 30, y: 8, width: 160, height: 134)
        let shape = Path(roundedRect: page, cornerRadius: 10)
        ctx.fill(shape, with: .color(Theme.card))
        ctx.stroke(shape, with: .color(Theme.ink.opacity(0.85)), lineWidth: 2.5)

        let perRow = 1.1
        let cycle = perRow * Double(rows.count)
        let local = t.truncatingRemainder(dividingBy: cycle)
        let current = Int(local / perRow)
        let progress = easeOut((local - Double(current) * perRow) / (perRow * 0.85))
        let left = page.minX + 16, full = page.width - 32
        var lensPoint = CGPoint(x: left, y: 0)
        for (i, fraction) in rows.enumerated() {
            let y = page.minY + 22 + CGFloat(i) * 22
            let w = full * fraction
            let done: CGFloat = i < current ? 1 : (i == current ? progress : 0)
            if done > 0 {
                ctx.fill(Path(roundedRect: CGRect(x: left - 5, y: y - 6, width: (w + 10) * done, height: 13), cornerRadius: 4),
                         with: .color(i == current ? Theme.highlighter : Theme.markerSoft))
            }
            ctx.fill(Path(roundedRect: CGRect(x: left, y: y - 2.5, width: w, height: 5), cornerRadius: 2.5),
                     with: .color(i <= current ? Theme.ink.opacity(0.75) : Theme.line))
            if i == current { lensPoint = CGPoint(x: left + w * done, y: y) }
        }
        var lens = ctx
        lens.translateBy(x: lensPoint.x + 6, y: lensPoint.y + 10)
        drawLens(lens, center: .zero, radius: 17, line: 3)
    }
}

/// A made-up letter with one line marked and explained: the product in one picture (as on the web sign-in page).
struct LetterDemo: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var explained = false

    var body: some View {
        VStack(alignment: .trailing, spacing: 0) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Finanzamt Musterstadt")
                    Spacer()
                    Text("02.12.2026")
                }
                .font(.caption2).foregroundStyle(Theme.inkFaint)
                Text("Bescheid über Einkommensteuer 2025").font(.system(.subheadline, design: .serif).weight(.bold))
                SkeletonBar(height: 6).frame(maxWidth: .infinity).padding(.trailing, 20)
                SkeletonBar(height: 6).frame(maxWidth: .infinity).padding(.trailing, 60)
                Text("Bitte zahlen Sie 312,00 € bis zum 15.01.2027.")
                    .font(.system(.footnote, design: .serif))
                    .foregroundStyle(Theme.ink)
                    .padding(.vertical, 2)
                    .markerSweep(delay: 0.5, fullHeight: true)
                SkeletonBar(height: 6).frame(maxWidth: .infinity).padding(.trailing, 36)
                SkeletonBar(height: 6).frame(maxWidth: .infinity).padding(.trailing, 110)
            }
            .environment(\.locale, Locale(identifier: "de"))
            .padding(16)
            .background(Theme.card, in: RoundedRectangle(cornerRadius: 10))
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.line))
            .shadow(color: Theme.ink.opacity(0.12), radius: 14, y: 8)
            .rotationEffect(.degrees(-1.5))

            VStack(alignment: .leading, spacing: 8) {
                Text("You must pay €312.00 to the tax office by 15 January 2027.")
                    .font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink)
                    .fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 6) {
                    Pill(text: "Found in the letter", kind: .ok, icon: "checkmark")
                    Pill(text: "15 Jan 2027")
                }
            }
            .padding(12)
            .frame(maxWidth: 290, alignment: .leading)
            .padding(.leading, 40)
            .background(Theme.card, in: RoundedRectangle(cornerRadius: 12))
            .overlay(alignment: .leading) {
                UnevenRoundedRectangle(topLeadingRadius: 12, bottomLeadingRadius: 12).fill(Theme.ok).frame(width: 5)
            }
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.line))
            .shadow(color: Theme.ink.opacity(0.16), radius: 16, y: 10)
            .rotationEffect(.degrees(1))
            .padding(.top, -18)
            .opacity(explained ? 1 : 0)
            .offset(y: explained || reduceMotion ? 0 : 16)
        }
        .accessibilityHidden(true)
        .onAppear {
            withAnimation(reduceMotion ? .easeOut(duration: 0.2) : Motion.bouncy.delay(1.2)) { explained = true }
        }
    }
}
