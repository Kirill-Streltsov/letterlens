// Draws the 1024 px app icon: an envelope under a highlighter-yellow lens on paper.
// Usage: swift scripts/make_icon.swift LetterLens/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png && sips -z 1024 1024 <same path> (Retina screens draw at 2x)
import AppKit

let size = 1024.0
let image = NSImage(size: NSSize(width: size, height: size))
image.lockFocus()
let ink = NSColor(srgbRed: 0.106, green: 0.145, blue: 0.251, alpha: 1)
NSColor(srgbRed: 0.957, green: 0.933, blue: 0.886, alpha: 1).setFill()
NSRect(x: 0, y: 0, width: size, height: size).fill()
let envelope = NSBezierPath(roundedRect: NSRect(x: 150, y: 300, width: 600, height: 430), xRadius: 40, yRadius: 40)
NSColor.white.setFill(); envelope.fill()
ink.setStroke(); envelope.lineWidth = 34; envelope.stroke()
let flap = NSBezierPath()
flap.move(to: NSPoint(x: 170, y: 700)); flap.line(to: NSPoint(x: 450, y: 480)); flap.line(to: NSPoint(x: 730, y: 700))
flap.lineWidth = 34; flap.lineJoinStyle = .round; flap.stroke()
let lens = NSBezierPath(ovalIn: NSRect(x: 520, y: 200, width: 330, height: 330))
NSColor(srgbRed: 1.0, green: 0.886, blue: 0.478, alpha: 0.92).setFill(); lens.fill()
lens.lineWidth = 34; lens.stroke()
let handle = NSBezierPath()
handle.move(to: NSPoint(x: 815, y: 235)); handle.line(to: NSPoint(x: 930, y: 110))
handle.lineWidth = 64; handle.lineCapStyle = .round; handle.stroke()
image.unlockFocus()
let rep = NSBitmapImageRep(data: image.tiffRepresentation!)!
let png = rep.representation(using: .png, properties: [:])!
try! png.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
