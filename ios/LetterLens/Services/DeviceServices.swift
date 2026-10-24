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

    private static func recognizePage(_ image: CGImage) async throws -> [RecognizedLine] {
        try await withCheckedThrowingContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                if let error { continuation.resume(throwing: error); return }
                let observations = request.results as? [VNRecognizedTextObservation] ?? []
                let lines = observations.compactMap { obs -> RecognizedLine? in
                    guard let candidate = obs.topCandidates(1).first else { return nil }
                    let box = obs.boundingBox
                    return RecognizedLine(text: candidate.string, x: box.minX, y: box.minY,
                                          width: box.width, height: box.height, confidence: Double(candidate.confidence))
                }
                continuation.resume(returning: lines)
            }
            request.recognitionLevel = .accurate
            request.recognitionLanguages = ["de-DE"]
            request.usesLanguageCorrection = true
            do {
                try VNImageRequestHandler(cgImage: image).perform([request])
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }
}

