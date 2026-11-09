package main

import (
	"fmt"
	"path/filepath"
	"runtime"
	"strings"

	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
)

type surface int

const (
	conversationSurface surface = iota
	workspaceSurface
)

type workspaceTab int

const (
	threadsTab workspaceTab = iota
	projectsTab
	issuesTab
	machinesTab
	workspaceTabCount
)

type workspaceFocus int

const (
	workspaceList workspaceFocus = iota
	workspaceDetails
)

type workspaceSource int

const (
	sampleSource workspaceSource = iota
	currentThreadSource
	currentProjectSource
	localMachineSource
)

type workspaceRow struct {
	title   string
	status  string
	summary string
	details string
	source  workspaceSource
}

type workspaceState struct {
	tab      workspaceTab
	selected [workspaceTabCount]int
	focus    workspaceFocus
	list     viewport.Model
	details  viewport.Model
	notice   string
}

func (m *model) canOpenWorkspace() bool {
	return m.surface == conversationSurface && m.focus == composerFocus && m.composer.Value() == ""
}

func (m *model) closeWorkspace() tea.Cmd {
	m.surface = conversationSurface
	return m.composer.Focus()
}

func (m *model) updateWorkspaceKey(msg tea.KeyPressMsg) tea.Cmd {
	rows := m.workspaceRows()
	selected := &m.workspace.selected[m.workspace.tab]
	switch msg.String() {
	case "esc":
		return m.closeWorkspace()
	case "left", "right", "1", "2", "3", "4":
		if msg.String() == "left" {
			m.workspace.tab = (m.workspace.tab + workspaceTabCount - 1) % workspaceTabCount
		} else if msg.String() == "right" {
			m.workspace.tab = (m.workspace.tab + 1) % workspaceTabCount
		} else {
			m.workspace.tab = workspaceTab(msg.String()[0] - '1')
		}
		m.workspace.notice = ""
		m.updateWorkspace(true)
	case "tab", "shift+tab":
		m.workspace.focus = (m.workspace.focus + 1) % 2
		m.updateWorkspace(false)
	case "up", "k", "down", "j", "home", "end":
		if m.workspace.focus == workspaceDetails {
			switch msg.String() {
			case "up", "k":
				m.workspace.details.ScrollUp(1)
			case "down", "j":
				m.workspace.details.ScrollDown(1)
			case "home":
				m.workspace.details.GotoTop()
			case "end":
				m.workspace.details.GotoBottom()
			}
			return nil
		}
		if len(rows) == 0 {
			return nil
		}
		switch msg.String() {
		case "up", "k":
			*selected = max(0, *selected-1)
		case "down", "j":
			*selected = min(len(rows)-1, *selected+1)
		case "home":
			*selected = 0
		case "end":
			*selected = len(rows) - 1
		}
		m.workspace.notice = ""
		m.updateWorkspace(true)
	case "pgup", "pgdown":
		m.workspace.focus = workspaceDetails
		if msg.String() == "pgup" {
			m.workspace.details.PageUp()
		} else {
			m.workspace.details.PageDown()
		}
		m.updateWorkspace(false)
	case "enter":
		if len(rows) == 0 {
			return nil
		}
		source := rows[*selected].source
		if source == currentThreadSource || source == currentProjectSource {
			return m.closeWorkspace()
		}
		m.workspace.focus = workspaceDetails
		if source == sampleSource {
			m.workspace.notice = "Sample preview only. No live resource is connected."
		}
		m.updateWorkspace(false)
	}
	return nil
}

func (m *model) workspaceRows() []workspaceRow {
	var rows []workspaceRow
	project := filepath.Base(m.project)
	switch m.workspace.tab {
	case threadsTab:
		title, latest, status := "New conversation", "No messages yet.", "Draft"
		if len(m.entries) > 0 {
			title = strings.SplitN(m.entries[0].text, "\n", 2)[0]
			status = "Ready"
		}
		for _, e := range m.entries {
			if (e.kind == userEntry || e.kind == assistantEntry) && e.text != "" {
				latest = e.text
			}
		}
		if m.lastResult == cancelled {
			status = "Stopped"
		}
		if m.active != nil {
			status = "Working"
		}
		rows = append(rows, workspaceRow{
			title: title, status: status, summary: project + " · local · in memory", source: currentThreadSource,
			details: "Current UI conversation\n\nProject\n" + m.project + "\n\nState\n" + status + "\n\nModel and effort\n" + m.session.modelName + " · " + m.session.effort + "\n\nBranch\n" + m.session.branch + "\n\nStorage\nIn memory. Discarded on exit.\n\nLatest message\n" + latest,
		})
	case projectsTab:
		rows = append(rows, workspaceRow{
			title: project, status: "Open", summary: m.project, source: currentProjectSource,
			details: "Current project\n\nDirectory\n" + m.project + "\n\nBranch\n" + m.session.branch + "\n\nMachine\nlocal\n\nConversation\nOne current in-memory conversation.\n\nEnter returns to that conversation.",
		})
	case machinesTab:
		rows = append(rows, workspaceRow{
			title: "local", status: "UI host", summary: runtime.GOOS + " · " + runtime.GOARCH, source: localMachineSource,
			details: "Local machine\n\nPlatform\n" + runtime.GOOS + " / " + runtime.GOARCH + "\n\nProject\n" + m.project + "\n\nExecution\nThis machine runs the UI preview. Agent work is simulated.\n\nRemote connections\nNot configured.",
		})
	}
	return append(rows, workspaceSamples(m.workspace.tab)...)
}

type workspaceLayout struct {
	wide         bool
	listWidth    int
	detailsWidth int
	listHeight   int
	detailHeight int
}

func (m *model) workspaceLayout() workspaceLayout {
	width, height := max(1, m.width-4), max(4, m.height-8)
	if m.width >= 100 {
		detailsWidth := max(36, width/3)
		return workspaceLayout{true, max(1, width-detailsWidth-3), detailsWidth, height - 1, height - 1}
	}
	listArea := min(8, max(3, height/2))
	return workspaceLayout{false, width, width, max(1, listArea-1), max(1, height-listArea-2)}
}

func (m *model) updateWorkspace(resetDetails bool) {
	layout := m.workspaceLayout()
	m.workspace.list.SetWidth(layout.listWidth)
	m.workspace.list.SetHeight(layout.listHeight)
	m.workspace.details.SetWidth(layout.detailsWidth)
	m.workspace.details.SetHeight(layout.detailHeight)
	rows := m.workspaceRows()
	selected := &m.workspace.selected[m.workspace.tab]
	*selected = max(0, min(*selected, len(rows)-1))
	var blocks []string
	for i, row := range rows {
		source := "current"
		if row.source == sampleSource {
			source = "sample"
		}
		prefix := "  "
		if i == *selected {
			prefix = "› "
		}
		line := workspaceColumns(prefix, row.title, row.status, source, layout.listWidth)
		if i == *selected && m.workspace.focus == workspaceList {
			line = mark.Render(line)
		} else {
			line = ink.Render(line)
		}
		blocks = append(blocks, line+"\n"+muted.Render(ansi.Truncate("  "+row.summary, layout.listWidth, "…")))
	}
	m.workspace.list.SetContent(strings.Join(blocks, "\n\n"))
	start := *selected * 3
	if start < m.workspace.list.YOffset() {
		m.workspace.list.SetYOffset(start)
	} else if start+2 > m.workspace.list.YOffset()+layout.listHeight {
		m.workspace.list.SetYOffset(start + 2 - layout.listHeight)
	}
	details := "No entries."
	if len(rows) > 0 {
		row := rows[*selected]
		source := muted.Render("Current state")
		if row.source == sampleSource {
			source = caution.Render("Sample data. Preview only.")
		}
		details = strong.Render(ansi.Wrap(row.title, layout.detailsWidth, "")) + "\n" + source + "\n\n" + ink.Render(ansi.Wrap(row.details, layout.detailsWidth, ""))
	}
	m.workspace.details.SetContent(details)
	if resetDetails {
		m.workspace.details.GotoTop()
	}
}

func workspaceColumns(prefix, title, status, source string, width int) string {
	titleWidth := max(1, width-24)
	name := lipgloss.NewStyle().Width(titleWidth).Render(ansi.Truncate(title, titleWidth, "…"))
	return ansi.Truncate(fmt.Sprintf("%s%s  %-11s  %-7s", prefix, name, status, source), width, "")
}

func (m *model) workspaceView() string {
	width := m.width - 4
	brand := mark.Render(" brunel ") + strong.Render("  Workspace")
	sampleLabel := "Sample data included"
	if width < 60 {
		sampleLabel = "Samples"
	}
	header := spread(brand, caution.Render(sampleLabel), width) + "\n" +
		muted.Render(ansi.Truncate(m.project, width, "…"))
	var tabs []string
	for i, title := range []string{"Threads", "Projects", "Issues", "Machines"} {
		if width >= 60 {
			title = " " + title + " "
		}
		if workspaceTab(i) == m.workspace.tab {
			tabs = append(tabs, mark.Render(title))
		} else {
			tabs = append(tabs, muted.Render(title))
		}
	}
	header += "\n" + strings.Join(tabs, " ") + "\n" + muted.Render(strings.Repeat("─", width))
	layout := m.workspaceLayout()
	listTitle := []string{"Thread", "Project", "Issue", "Machine"}[m.workspace.tab]
	list := muted.Render(workspaceColumns("  ", listTitle, "State", "Source", layout.listWidth)) + "\n" + m.workspace.list.View()
	detailsTitle := strong.Render("Details")
	if m.workspace.focus == workspaceDetails {
		detailsTitle = mark.Render(" Details ")
	}
	details := detailsTitle + "\n" + m.workspace.details.View()
	var body string
	if layout.wide {
		divider := muted.Render(strings.TrimSuffix(strings.Repeat(" │ \n", layout.listHeight+1), "\n"))
		body = lipgloss.JoinHorizontal(lipgloss.Top, list, divider, details)
	} else {
		body = list + "\n" + muted.Render(strings.Repeat("─", width)) + "\n" + details
	}
	notice := m.workspace.notice
	if notice == "" {
		notice = "Current state and labelled samples. Enter opens only the current conversation."
	}
	if m.workspace.tab == issuesTab && m.workspace.notice == "" {
		notice = "No issue tracker connected. These rows are sample data."
	}
	help := "←→ tabs · ↑↓ move · tab pane · pgup pgdn details · enter inspect/open · esc conversation · ^c quit"
	if width < 100 {
		help = "←→ tabs · ↑↓ select · tab pane · enter open · esc back · ^c quit"
	}
	if width < 76 {
		help = "←→ tabs · tab pane · esc · ^c quit"
	}
	content := strings.Join([]string{header, body, muted.Render(ansi.Truncate(notice, width, "…")), muted.Render(ansi.Truncate(help, width, ""))}, "\n")
	return lipgloss.NewStyle().Padding(1, 2).Render(content)
}
