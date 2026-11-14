import Foundation
import CoreGraphics

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
