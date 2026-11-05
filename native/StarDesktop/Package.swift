// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "StarDesktop",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "StarDesktop", targets: ["StarDesktop"])],
    targets: [.executableTarget(name: "StarDesktop")]
)
