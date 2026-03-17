import Foundation
import Combine
import AppKit

@MainActor
final class SettingsViewModel: ObservableObject {

    @Published var smallestKey = ""
    @Published var userName = ""
    @Published var isLoading = false
    @Published var saveStatus: String?
    @Published var removeFillerWords = true
    @Published var customFillerWords: [String] = []
    @Published var fillerWordsCsv = ""

    private let api = APIClient.shared
    init() {}

    // MARK: - Load

    func load() async {
        isLoading = true
        defer { isLoading = false }

        if let keys: ApiKeysResponse = try? await api.invoke("has_api_keys") {
            smallestKey = keys.smallest ?? ""
        }
        if let name: String = try? await api.invoke("get_user_name") {
            userName = name
        }
        if let settings: AdvancedSettings = try? await api.invoke("get_advanced_settings") {
            removeFillerWords = settings.fillerRemoval
        }
        if let words: [String] = try? await api.invoke("get_filler_words") {
            customFillerWords = words
            fillerWordsCsv = words.joined(separator: ", ")
        }
    }

    // MARK: - Save API Keys / Profile

    func saveSmallestKey() async -> Bool {
        do {
            try await api.invokeVoid("save_api_key", body: ["service": "smallest", "key": smallestKey])
            return true
        } catch {
            return false
        }
    }

    func saveUserName() async {
        try? await api.invokeVoid("save_user_name", body: ["name": userName])
        flashStatus("Saved")
    }

    // MARK: - Filler words

    func saveRemoveFillerWords(_ enabled: Bool) async {
        try? await api.invokeVoid("save_advanced_setting", body: ["key": "filler_removal", "value": enabled])
    }

    func saveFillerWordsCsv(_ csv: String) async {
        let parsed = csv
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() }
            .filter { !$0.isEmpty }
        customFillerWords = parsed
        fillerWordsCsv = parsed.joined(separator: ", ")
        try? await api.invokeVoid("save_filler_words", body: ["words": parsed])
    }


    // MARK: - Helpers

    private func flashStatus(_ message: String) {
        saveStatus = message
        Task {
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            saveStatus = nil
        }
    }

    private struct ApiKeysResponse: Decodable {
        let smallest: String?
    }

    private struct AdvancedSettings: Decodable {
        let fillerRemoval: Bool
    }
}
