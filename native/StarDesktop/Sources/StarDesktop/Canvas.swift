import AppKit
import SwiftUI

struct ScreenshotCanvas: NSViewRepresentable {
    let frame: FrozenFrame?
    let enabled: Bool
    let onPoint: (CGPoint) -> Void
    let onRegion: (PixelRegion) -> Void

    func makeNSView(context: Context) -> CanvasView { CanvasView() }

    func updateNSView(_ view: CanvasView, context: Context) {
        let changed = view.frameID != frame?.id
        if changed { view.selected = nil; view.start = nil }
        view.frameID = frame?.id
        view.image = frame?.image
        view.pixels = CGSize(width: CGFloat(frame?.width ?? 1), height: CGFloat(frame?.height ?? 1))
        view.enabled = enabled
        view.onPoint = onPoint
        view.onRegion = onRegion
        if changed { view.needsDisplay = true }
    }
}

final class CanvasView: NSView {
    var frameID: String?
    var image: NSImage?
    var pixels = CGSize(width: 1, height: 1)
    var enabled = false
    var start: CGPoint?
    var selected: PixelRegion?
    var onPoint: ((CGPoint) -> Void)?
    var onRegion: ((PixelRegion) -> Void)?
    override var isFlipped: Bool { true }

    private var imageRect: CGRect {
        let scale = min(bounds.width / pixels.width, bounds.height / pixels.height)
        let size = CGSize(width: pixels.width * scale, height: pixels.height * scale)
        return CGRect(x: (bounds.width - size.width) / 2, y: (bounds.height - size.height) / 2,
                      width: size.width, height: size.height)
    }

    override func draw(_ dirtyRect: NSRect) {
        NSColor.controlBackgroundColor.setFill()
        bounds.fill()
        guard let image else { return }
        image.draw(in: imageRect, from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
        if let selected {
            let scaleX = imageRect.width / pixels.width, scaleY = imageRect.height / pixels.height
            let rect = CGRect(x: imageRect.minX + CGFloat(selected.left) * scaleX,
                              y: imageRect.minY + CGFloat(selected.top) * scaleY,
                              width: CGFloat(selected.width) * scaleX, height: CGFloat(selected.height) * scaleY)
            NSColor.controlAccentColor.setStroke()
            let path = NSBezierPath(rect: rect)
            path.lineWidth = 2
            path.stroke()
        }
    }

    private func pixel(_ event: NSEvent, requireInside: Bool = false) -> CGPoint? {
        guard enabled, image != nil, imageRect.width > 0, imageRect.height > 0 else { return nil }
        let point = convert(event.locationInWindow, from: nil)
        if requireInside && !imageRect.contains(point) { return nil }
        return CGPoint(x: floor(max(0, min(pixels.width - 1, (point.x - imageRect.minX) * pixels.width / imageRect.width))),
                       y: floor(max(0, min(pixels.height - 1, (point.y - imageRect.minY) * pixels.height / imageRect.height))))
    }

    override func mouseDown(with event: NSEvent) {
        start = pixel(event, requireInside: true)
        selected = nil
        needsDisplay = true
    }

    override func mouseDragged(with event: NSEvent) {
        guard let start, let current = pixel(event) else { return }
        selected = region(start, current)
        needsDisplay = true
    }

    override func mouseUp(with event: NSEvent) {
        guard let first = start, let last = pixel(event) else { start = nil; return }
        start = nil
        if abs(first.x - last.x) < 3 && abs(first.y - last.y) < 3 {
            selected = nil
            onPoint?(last)
        } else {
            let result = region(first, last)
            selected = result
            onRegion?(result)
        }
        needsDisplay = true
    }

    private func region(_ a: CGPoint, _ b: CGPoint) -> PixelRegion {
        PixelRegion(left: Int(min(a.x, b.x)), top: Int(min(a.y, b.y)),
                    width: max(1, Int(abs(a.x - b.x))), height: max(1, Int(abs(a.y - b.y))))
    }
}
