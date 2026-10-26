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

/// VisionKit document camera: edge detection, perspective correction, multi-page.
struct DocumentScanner: UIViewControllerRepresentable {
    var onFinish: ([CGImage]) -> Void
    var onCancel: () -> Void

    static var isAvailable: Bool { VNDocumentCameraViewController.isSupported }

    func makeUIViewController(context: Context) -> VNDocumentCameraViewController {
        let controller = VNDocumentCameraViewController()
        controller.delegate = context.coordinator
        return controller
    }

    func updateUIViewController(_ controller: VNDocumentCameraViewController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    final class Coordinator: NSObject, VNDocumentCameraViewControllerDelegate {
        let parent: DocumentScanner
        init(_ parent: DocumentScanner) { self.parent = parent }

        func documentCameraViewController(_ controller: VNDocumentCameraViewController, didFinishWith scan: VNDocumentCameraScan) {
            let images = (0..<min(scan.pageCount, 6)).compactMap { scan.imageOfPage(at: $0).cgImage }
            parent.onFinish(images)
        }

        func documentCameraViewControllerDidCancel(_ controller: VNDocumentCameraViewController) { parent.onCancel() }

        func documentCameraViewController(_ controller: VNDocumentCameraViewController, didFailWithError error: Error) {
            parent.onCancel()
        }
    }
}

// MARK: - Calendar and reminders

enum ReminderService {
    /// Adds an all-day event with an alarm three days before. Needs write-only calendar access.
    static func addToCalendar(title: String, iso: String, notes: String) async throws {
        let store = EKEventStore()
        guard try await store.requestWriteOnlyAccessToEvents() else {
            throw NSError(domain: "LetterLens", code: 1, userInfo: [NSLocalizedDescriptionKey: "Calendar access was not allowed."])
        }
        guard let date = Deadlines.date(fromISO: iso) else { return }
        let event = EKEvent(eventStore: store)
        event.title = title
        event.notes = notes
        event.isAllDay = true
        event.startDate = Calendar.current.startOfDay(for: date)
        event.endDate = event.startDate
        event.calendar = store.defaultCalendarForNewEvents
        event.addAlarm(EKAlarm(relativeOffset: -3 * 86_400 + 9 * 3_600))
        try store.save(event, span: .thisEvent)
    }

    /// Local notification on the morning three days before the deadline.
    static func scheduleReminder(id: String, title: String, iso: String) async throws -> Date? {
        let center = UNUserNotificationCenter.current()
        guard try await center.requestAuthorization(options: [.alert, .sound]) else { return nil }
        guard let when = Deadlines.reminderDate(for: iso) else { return nil }
        let content = UNMutableNotificationContent()
        content.title = "Deadline soon"
        content.body = title
        content.sound = .default
        let parts = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute], from: when)
        let request = UNNotificationRequest(identifier: id, content: content,
                                            trigger: UNCalendarNotificationTrigger(dateMatching: parts, repeats: false))
        try await center.add(request)
        return when
    }
}

// MARK: - StoreKit 2

@MainActor
final class StoreService {
    static let plusProductID = "app.letterlens.plus.monthly"
    var onVerifiedTransaction: ((String) -> Void)?
    private var updates: Task<Void, Never>?

    func listenForTransactions() {
        updates?.cancel()
        updates = Task { [weak self] in
            for await result in StoreKit.Transaction.updates {
                await self?.handle(result)
            }
        }
    }

    func plusProduct() async throws -> Product? {
        try await Product.products(for: [Self.plusProductID]).first
    }

    /// The app account token binds the purchase to the LetterLens user id; the server checks it.
    func purchase(_ product: Product, userId: String) async throws {
        var options: Set<Product.PurchaseOption> = []
        if let token = UUID(uuidString: userId) { options.insert(.appAccountToken(token)) }
        if case .success(let result) = try await product.purchase(options: options) {
            await handle(result)
        }
    }

    func restore() async throws {
        try await AppStore.sync()
        for await result in StoreKit.Transaction.currentEntitlements { await handle(result) }
    }

    private func handle(_ result: VerificationResult<StoreKit.Transaction>) async {
        guard case .verified(let transaction) = result else { return }
        onVerifiedTransaction?(result.jwsRepresentation)
        await transaction.finish()
    }
}
