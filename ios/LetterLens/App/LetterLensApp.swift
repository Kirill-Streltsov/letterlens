import LetterLensCore
import SwiftUI

@main
struct LetterLensApp: App {
    @State private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(model)
                .task { await model.start() }
                .tint(Theme.ink)
        }
    }
}

