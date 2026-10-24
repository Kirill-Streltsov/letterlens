import EventKit
import Foundation
import LetterLensCore
import StoreKit
import SwiftUI
import UserNotifications
import Vision
import VisionKit

// MARK: - On-device text recognition (Apple Vision). Images never leave the phone.

enum TextRecognizer {
    static func recognize(_ images: [CGImage]) async throws -> LetterDocument {
        var pages: [[RecognizedLine]] = []
        for image in images {
            pages.append(try await recognizePage(image))
        }
        return DocumentBuilder.build(pages: pages)
    }

