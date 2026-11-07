import Foundation

struct PixelRegion: Equatable {
    let left: Int
    let top: Int
    let width: Int
    let height: Int
    var payload: [String: Int] { ["left": left, "top": top, "width": width, "height": height] }
}


func canvasRegion(_ a: CGPoint, _ b: CGPoint) -> PixelRegion {
    PixelRegion(left: Int(min(a.x, b.x)), top: Int(min(a.y, b.y)),
                width: Int(abs(a.x - b.x)) + 1, height: Int(abs(a.y - b.y)) + 1)
}
