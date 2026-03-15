import SwiftUI
import ServiceManagement

struct SettingsView: View {
    @StateObject private var vm = SettingsViewModel()
    @State private var selectedTab = "keys"

    var body: some View {
        TabView(selection: $selectedTab) {
            APIKeysTab(vm: vm)
                .tabItem { Label("API Keys", systemImage: "key.fill") }
                .tag("keys")

            ProfileTab(vm: vm)
                .tabItem { Label("Profile", systemImage: "person.fill") }
                .tag("profile")

            if #available(macOS 13, *) {
                GeneralTab()
                    .tabItem { Label("General", systemImage: "gearshape") }
                    .tag("general")
            }
        }
        .frame(width: 560, height: 440)
        .task { await vm.load() }
    }
}

// MARK: - API Keys

private struct APIKeysTab: View {
    @ObservedObject var vm: SettingsViewModel
    @State private var smallestSaveState: SaveState = .idle

    enum SaveState { case idle, saving, saved, error }

    var body: some View {
        Form {
            Section {
                HStack {
                    SecureField("Smallest AI API Key", text: $vm.smallestKey)
                        .textFieldStyle(.roundedBorder)
                        .onChange(of: vm.smallestKey) { _ in smallestSaveState = .idle }
                    saveButton(state: smallestSaveState, disabled: vm.smallestKey.isEmpty) {
                        smallestSaveState = .saving
                        let ok = await vm.saveSmallestKey()
                        smallestSaveState = ok ? .saved : .error
                    }
                }
                saveHint(state: smallestSaveState, hint: "Used for real-time speech-to-text.")
            } header: { Text("Smallest AI") }
        }
        .formStyle(.grouped)
        .padding()
    }

    @ViewBuilder
    private func saveButton(state: SaveState, disabled: Bool, action: @escaping () async -> Void) -> some View {
        Button {
            Task { await action() }
        } label: {
            switch state {
            case .saving: ProgressView().controlSize(.small)
            case .saved:  Label("Saved", systemImage: "checkmark").foregroundStyle(.green)
            case .error:  Label("Error", systemImage: "xmark.circle").foregroundStyle(.red)
            case .idle:   Text("Save")
            }
        }
        .disabled(disabled || state == .saving)
        .frame(minWidth: 64)
    }

    @ViewBuilder
    private func saveHint(state: SaveState, hint: String) -> some View {
        switch state {
        case .error:
            Text("Could not save — is the MiniFlow engine running?")
                .font(.caption).foregroundStyle(.red)
        default:
            Text(hint).font(.caption).foregroundStyle(.secondary)
        }
    }
}


// MARK: - Profile

private struct ProfileTab: View {
    @ObservedObject var vm: SettingsViewModel

    var body: some View {
        Form {
            Section {
                HStack {
                    TextField("Your name", text: $vm.userName)
                        .textFieldStyle(.roundedBorder)
                    Button("Save") {
                        Task { await vm.saveUserName() }
                    }
                    .disabled(vm.userName.isEmpty)
                }
                Text("Used to personalise emails and messages.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } header: { Text("Display Name") }

            if let status = vm.saveStatus {
                Text(status).foregroundStyle(.green).font(.caption)
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - General

@available(macOS 13, *)
private struct GeneralTab: View {

    var body: some View {
        Form {
            Section {
                Toggle(
                    "Launch at Login",
                    isOn: Binding<Bool>(
                        get: { SMAppService.mainApp.status == .enabled },
                        set: { enabled in
                            if enabled { try? SMAppService.mainApp.register() }
                            else       { try? SMAppService.mainApp.unregister() }
                        }
                    )
                )
                Text("MiniFlow will start automatically when you log in.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } header: { Text("Startup") }

            Section {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Accessibility Permission")
                            .font(.system(size: 13))
                        Text("Required for MiniFlow to type text into other apps. After granting, you may need to restart MiniFlow.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button("Open Settings") {
                        NSWorkspace.shared.open(
                            URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!
                        )
                    }
                    .buttonStyle(.borderless)
                    .foregroundColor(.accentColor)
                    .font(.system(size: 12, weight: .medium))
                }
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Fn Key Setting")
                            .font(.system(size: 13))
                        Text("Set 'Press Fn key to' -> 'Do Nothing' in Keyboard settings.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button("Keyboard Settings") {
                        NSWorkspace.shared.open(
                            URL(string: "x-apple.systempreferences:com.apple.preference.keyboard")!
                        )
                    }
                    .buttonStyle(.borderless)
                    .foregroundColor(.accentColor)
                    .font(.system(size: 12, weight: .medium))
                }
            } header: { Text("Permissions") }
        }
        .formStyle(.grouped)
        .padding()
    }
}
