import LetterLensCore
import SwiftUI
import UIKit

@main
struct LetterLensApp: App {
    @State private var model = AppModel()

    init() {
        // Serif navigation titles, like the web's headings.
        func serif(_ style: UIFont.TextStyle, _ weight: UIFont.Weight) -> UIFont {
            let base = UIFont.preferredFont(forTextStyle: style)
            let descriptor = base.fontDescriptor.withDesign(.serif)?
                .addingAttributes([.traits: [UIFontDescriptor.TraitKey.weight: weight]]) ?? base.fontDescriptor
            return UIFont(descriptor: descriptor, size: base.pointSize)
        }
        let bar = UINavigationBar.appearance()
        bar.largeTitleTextAttributes = [.font: serif(.largeTitle, .bold), .foregroundColor: UIColor(Theme.ink)]
        bar.titleTextAttributes = [.font: serif(.headline, .semibold), .foregroundColor: UIColor(Theme.ink)]
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(model)
                .task { await model.start() }
                .tint(Theme.ink)
        }
    }
}

struct RootView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        ZStack {
            switch model.phase {
            case .loading:
                LaunchView().transition(.opacity)
            case .signedOut:
                SignInView().transition(.opacity)
            case .signedIn:
                TabView {
                    NavigationStack { LettersView() }
                        .tabItem { Label("Letters", systemImage: "envelope.open") }
                    NavigationStack { SettingsView() }
                        .tabItem { Label("Settings", systemImage: "gearshape") }
                }
                .transition(.opacity.combined(with: .scale(scale: 1.02)))
            }
        }
        .animation(.easeInOut(duration: 0.35), value: model.phase)
        .alert("Something went wrong", isPresented: Binding(get: { model.error != nil }, set: { if !$0 { model.error = nil } })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(model.error ?? "")
        }
    }
}

/// Shown while the session is restored: the logo with a gently breathing lens.
struct LaunchView: View {
    @State private var pulse = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        VStack(spacing: 14) {
            LogoMark(size: 88)
                .scaleEffect(pulse ? 1.06 : 1)
                .animation(reduceMotion ? nil : .easeInOut(duration: 0.9).repeatForever(autoreverses: true), value: pulse)
            Text("LetterLens").font(Theme.title(26).weight(.bold)).foregroundStyle(Theme.ink)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .paperBackground()
        .onAppear { pulse = true }
        .accessibilityLabel("Loading LetterLens")
    }
}
