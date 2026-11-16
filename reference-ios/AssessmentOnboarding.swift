// Референс SwiftUI: тот же визуальный язык, что и Android Compose.
// Скопируй в iOS target (Xcode 15+). Подставь свои ассеты / AsyncImage.
import SwiftUI

enum OnboardingColor {
    static let background = Color(red: 0.99, green: 0.95, blue: 0.95)
    static let textPrimary = Color(red: 0.04, green: 0.04, blue: 0.04)
    static let textSecondary = Color(red: 0.42, green: 0.42, blue: 0.45)
    static let orange = Color(red: 1.0, green: 0.42, blue: 0)
    static let toggleBlue = Color(red: 0.18, green: 0.44, blue: 0.93)
    static let pillIdle = Color(red: 0.94, green: 0.91, blue: 0.91)
}

struct AssessmentChrome<Content: View>: View {
    let step: Int
    let total: Int
    let title: String
    let canContinue: Bool
    let onBack: () -> Void
    let onContinue: () -> Void
    @ViewBuilder var content: () -> Content

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Button(action: onBack) {
                    Text("‹").font(.title2).foregroundStyle(OnboardingColor.textPrimary)
                }
                Text(title)
                    .font(.headline.weight(.semibold))
                    .foregroundStyle(OnboardingColor.textPrimary)
                    .frame(maxWidth: .infinity)
                Text("\(step) из \(total)")
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(OnboardingColor.textSecondary)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(OnboardingColor.pillIdle, in: Capsule())
            }
            .padding(.horizontal, 28)
            .padding(.vertical, 8)

            ScrollView {
                content()
                    .padding(.horizontal, 28)
                    .padding(.top, 36)
            }
            .frame(maxHeight: .infinity)

            Button(action: onContinue) {
                HStack {
                    Text("Продолжить")
                    Text("→")
                }
                .font(.headline.weight(.semibold))
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .background(canContinue ? OnboardingColor.textPrimary : Color(white: 0.75), in: Capsule())
            }
            .disabled(!canContinue)
            .padding(.horizontal, 28)
            .padding(.bottom, 12)
        }
        .background(OnboardingColor.background.ignoresSafeArea())
    }
}

// Дальше: вынеси 4 шага (пол, вес, рост, возраст) в отдельные struct View,
// используй AssessmentChrome с step 1...4 и теми же отступами/цветами.
