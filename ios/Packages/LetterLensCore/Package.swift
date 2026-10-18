// swift-tools-version: 6.0
// Platform-independent core of the iOS app: API models, API client, PKCE, OCR line
// ordering and deadline logic. Tested on macOS with `swift test` (no simulator needed).
import PackageDescription

let package = Package(
    name: "LetterLensCore",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "LetterLensCore", targets: ["LetterLensCore"])],
    targets: [
        .target(name: "LetterLensCore"),
        .testTarget(name: "LetterLensCoreTests", dependencies: ["LetterLensCore"]),
    ]
)
