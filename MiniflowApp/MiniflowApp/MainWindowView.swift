import SwiftUI

struct MainWindowView: View {
    @ObservedObject var vm: AgentViewModel
    @State private var selectedTab = "home"
    @State private var showSettings = false
    var onSettings: () -> Void

    var body: some View {
        HStack(spacing: 0) {

            // Left sidebar (200pt fixed)
            SidebarView(vm: vm, selectedTab: $selectedTab, onSettings: onSettings)

            // Main content area (white card)
            ZStack(alignment: .topLeading) {
                Color.white

                Group {
                    switch selectedTab {
                    case "dictionary":
                        DictionaryTab()
                    case "snippets":
                        SnippetsTab()
                    default:
                        HomeTab(vm: vm)
                    }
                }
            }
        }
        .frame(width: 1200, height: 800)
        .background(Color.bgWarm)
    }
}
