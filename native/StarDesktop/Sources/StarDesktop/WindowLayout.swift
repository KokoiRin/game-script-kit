import Foundation
import CoreGraphics

func companionFrame(target: CGRect, consoleSize: CGSize, desktopTop: CGFloat) -> CGRect {
    CGRect(x: target.maxX, y: desktopTop - target.minY - consoleSize.height,
           width: consoleSize.width, height: consoleSize.height)
}

struct CompanionVisibility {
    private var wasFront = false
    private var mouseWasDown = false

    mutating func shouldReveal(targetIsFront: Bool, mouseDown: Bool, clickInsideTarget: Bool) -> Bool {
        let reveal = targetIsFront && (!wasFront || (mouseDown && !mouseWasDown && clickInsideTarget))
        wasFront = targetIsFront
        mouseWasDown = mouseDown
        return reveal
    }
}

func usesCompactLayout(for tab: String) -> Bool {
    tab == "observe" || tab == "run"
}

func sidePanelFrame(in visibleFrame: CGRect) -> CGRect {
    let size = CGSize(width: min(520, visibleFrame.width), height: min(820, visibleFrame.height))
    return CGRect(x: visibleFrame.maxX - size.width, y: visibleFrame.maxY - size.height,
                  width: size.width, height: size.height)
}

func windowFrame(_ preferred: CGRect, fitting visibleFrame: CGRect) -> CGRect {
    let size = CGSize(width: min(preferred.width, visibleFrame.width),
                      height: min(preferred.height, visibleFrame.height))
    return CGRect(x: max(visibleFrame.minX, min(preferred.minX, visibleFrame.maxX - size.width)),
                  y: max(visibleFrame.minY, min(preferred.minY, visibleFrame.maxY - size.height)),
                  width: size.width, height: size.height)
}
