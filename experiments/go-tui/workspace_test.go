package main

import (
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/ansi"
)

func TestWorkspaceEntryIsOnlyAvailableFromAnEmptyComposer(t *testing.T) {
	m := testModel(120, 40)
	if !strings.Contains(ansi.Strip(m.View().Content), "← workspace") {
		t.Fatal("an empty composer must advertise the workspace action")
	}
	press(m, tea.KeyLeft, 0)
	if m.surface != workspaceSurface || m.composer.Focused() {
		t.Fatal("Left from an empty composer must open the workspace and blur input")
	}
	m.Update(tea.PasteMsg{Content: "this must not enter the hidden composer"})
	if m.composer.Value() != "" {
		t.Fatal("workspace paste changed the conversation draft")
	}
	press(m, tea.KeyEscape, 0)
	if m.surface != conversationSurface || !m.composer.Focused() {
		t.Fatal("Escape must restore the conversation composer")
	}
	m.Update(tea.PasteMsg{Content: "abc"})
	press(m, tea.KeyLeft, 0)
	m.Update(tea.KeyPressMsg{Code: 'X', Text: "X"})
	if m.surface != conversationSurface || m.composer.Value() != "abXc" {
		t.Fatal("Left must retain ordinary cursor editing when a draft exists")
	}
	m = testModel(80, 24)
	m.Update(tea.PasteMsg{Content: " "})
	press(m, tea.KeyLeft, 0)
	if m.surface != conversationSurface {
		t.Fatal("whitespace is draft text and must not open the workspace")
	}
	m = testModel(80, 24)
	press(m, tea.KeyF2, 0)
	press(m, tea.KeyLeft, 0)
	if m.surface != conversationSurface || m.setting != 1 {
		t.Fatal("settings arrows must keep their existing meaning")
	}
}

func TestWorkspacePreservesConversationAndKeepsTheHiddenRunAlive(t *testing.T) {
	m := testModel(80, 24)
	sendPrompt(m, "Keep this thread alive")
	for range 9 {
		advanceDemo(m)
	}
	press(m, 'o', tea.ModCtrl)
	press(m, tea.KeyPgUp, 0)
	selected, offset := m.selected, m.transcript.YOffset()
	if m.transcript.AtBottom() {
		t.Fatal("test setup must leave the transcript scrolled up")
	}
	runID := m.active.id
	press(m, tea.KeyLeft, 0)
	press(m, tea.KeyEscape, 0)
	if m.active == nil || m.active.id != runID {
		t.Fatal("Escape from Workspace cancelled the conversation run")
	}
	press(m, tea.KeyLeft, 0)
	m.Update(branchMsg("topic/workspace"))
	finishDemo(m)
	if m.surface != workspaceSurface || m.workspaceRows()[0].status != "Ready" {
		t.Fatal("the hidden run must finish and update the workspace's current row")
	}
	if !strings.Contains(ansi.Strip(m.workspace.details.GetContent()), "topic/workspace") {
		t.Fatal("shared branch messages were dropped while browsing")
	}
	press(m, tea.KeyEnter, 0)
	if m.surface != conversationSurface || m.selected != selected || m.transcript.YOffset() != offset {
		t.Fatal("returning reset transcript selection or scroll position")
	}
	if !m.entries[selected].expanded || !strings.Contains(m.transcript.GetContent(), "The activity above is scripted.") {
		t.Fatal("returning lost expanded details or completed output")
	}
}

func TestWorkspaceSamplesRemainPreviewsAndCurrentRowsReturn(t *testing.T) {
	m := testModel(120, 40)
	press(m, tea.KeyLeft, 0)
	press(m, tea.KeyDown, 0)
	press(m, tea.KeyEnter, 0)
	if m.surface != workspaceSurface || m.active != nil || m.generation != 0 {
		t.Fatal("a sample thread must not open a live conversation or start work")
	}
	if !strings.Contains(ansi.Strip(m.workspace.details.GetContent()), "Sample data. Preview only.") {
		t.Fatal("sample details must label their source")
	}
	press(m, '3', 0)
	for _, row := range m.workspaceRows() {
		if row.source != sampleSource {
			t.Fatal("unconnected issue ingestion must not expose a current issue")
		}
	}
	if !strings.Contains(ansi.Strip(m.View().Content), "No issue tracker connected.") {
		t.Fatal("the Issues tab must disclose that its rows are samples")
	}
	press(m, '4', 0)
	press(m, tea.KeyEnter, 0)
	if m.surface != workspaceSurface || m.workspace.focus != workspaceDetails {
		t.Fatal("the local machine is inspectable and must not open another session")
	}
	press(m, '2', 0)
	press(m, tea.KeyEnter, 0)
	if m.surface != conversationSurface || !m.composer.Focused() {
		t.Fatal("the current project must return to its existing conversation")
	}
}

func TestWorkspaceTabsRetainSelectionsAndDetailsCanScroll(t *testing.T) {
	m := testModel(80, 24)
	press(m, tea.KeyLeft, 0)
	press(m, tea.KeyDown, 0)
	press(m, tea.KeyDown, 0)
	press(m, tea.KeyRight, 0)
	press(m, tea.KeyDown, 0)
	press(m, tea.KeyLeft, 0)
	if m.workspace.tab != threadsTab || m.workspace.selected[threadsTab] != 2 {
		t.Fatal("switching tabs must preserve the selected row")
	}
	if !strings.Contains(ansi.Strip(m.workspace.details.GetContent()), "workflow waiting for input") {
		t.Fatal("details did not follow the restored selection")
	}
	press(m, tea.KeyTab, 0)
	press(m, tea.KeyEnd, 0)
	if m.workspace.focus != workspaceDetails || m.workspace.details.YOffset() == 0 {
		t.Fatal("the focused details pane must scroll")
	}
	selection := m.workspace.selected[threadsTab]
	press(m, tea.KeyUp, 0)
	if m.workspace.selected[threadsTab] != selection {
		t.Fatal("detail navigation changed the list selection")
	}
	press(m, tea.KeyTab, tea.ModShift)
	if m.workspace.focus != workspaceList {
		t.Fatal("Shift+Tab must restore list focus")
	}
}

func TestWorkspaceViewsFitWideAndStackedTerminals(t *testing.T) {
	m := testModel(120, 40)
	m.project = "/Users/alex/Projects/" + strings.Repeat("界面", 30)
	m.Update(branchMsg(strings.Repeat("long-branch-", 30)))
	sendPrompt(m, "Inspect 界面 🛠 "+strings.Repeat("longtitle", 40))
	press(m, tea.KeyLeft, 0)
	for _, size := range [][2]int{{144, 48}, {120, 40}, {100, 24}, {99, 24}, {80, 24}, {59, 18}, {40, 16}, {20, 8}} {
		m.Update(tea.WindowSizeMsg{Width: size[0], Height: size[1]})
		for _, tab := range []rune{'1', '2', '3', '4'} {
			press(m, tab, 0)
			press(m, tea.KeyEnd, 0)
			for range 2 {
				content := m.View().Content
				lines := strings.Split(content, "\n")
				if len(lines) > size[1] {
					t.Errorf("%dx%d tab %c has %d rows", size[0], size[1], tab, len(lines))
				}
				for i, line := range lines {
					if width := ansi.StringWidth(line); width > size[0] {
						t.Errorf("%dx%d tab %c row %d has width %d", size[0], size[1], tab, i, width)
					}
				}
				if size[0] >= 40 {
					plain := ansi.Strip(content)
					for _, want := range []string{"Threads", "Projects", "Issues", "Machines", "^c quit"} {
						if !strings.Contains(plain, want) {
							t.Errorf("%dx%d tab %c lost %q", size[0], size[1], tab, want)
						}
					}
				}
				press(m, tea.KeyTab, 0)
			}
		}
	}
}

func TestWorkspaceShowsAnImmediatelyStoppedRun(t *testing.T) {
	m := testModel(120, 40)
	sendPrompt(m, "Stop before any agent output")
	press(m, tea.KeyEscape, 0)
	press(m, tea.KeyF2, 0)
	press(m, tea.KeyEnter, 0)
	press(m, tea.KeyEscape, 0)
	press(m, tea.KeyLeft, 0)
	if !strings.Contains(ansi.Strip(m.View().Content), "Stopped") {
		t.Fatal("changing settings must not erase the stopped run's outcome")
	}
}
