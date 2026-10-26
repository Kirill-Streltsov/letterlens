import LetterLensCore
import SwiftUI

struct LetterDetailView: View {
    let letterId: String
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var letter: LetterView?
    @State private var language = "en"
    @State private var highlighted: Set<String> = []
    @State private var showOriginal = false
    @State private var showShare = false
    @State private var confirmDelete = false
    @State private var toast: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let letter {
                    content(letter)
                } else {
                    ProgressView().frame(maxWidth: .infinity).padding(.top, 80)
                }
            }
            .padding()
        }
