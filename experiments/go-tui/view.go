package main

import (
	"fmt"
	"path/filepath"
	"strings"

	"charm.land/bubbles/v2/textarea"
	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
)

var (
	blue    = lipgloss.Color("#003366")
	white   = lipgloss.Color("#F4F8FF")
	pale    = lipgloss.Color("#A9D4FF")
	amber   = lipgloss.Color("#FFE4A3")
	ink     = lipgloss.NewStyle().Foreground(white)
	muted   = lipgloss.NewStyle().Foreground(pale)
	strong  = lipgloss.NewStyle().Foreground(white).Bold(true)
	caution = lipgloss.NewStyle().Foreground(amber)
	mark    = lipgloss.NewStyle().Foreground(blue).Background(white).Bold(true)
)

func composerStyles() textarea.Styles {
	state := textarea.StyleState{
		Base: ink, Text: ink, CursorLine: ink, Prompt: strong,
		Placeholder: muted, EndOfBuffer: muted,
	}
	return textarea.Styles{
		Focused: state, Blurred: state,
		Cursor: textarea.CursorStyle{Color: white, Shape: tea.CursorBar, Blink: true},
	}
}

func (m *model) transcriptWidth() int {
	width := m.width - 4
	if m.width >= 110 {
		width -= 31
	}
	return max(1, width)
}

func (m *model) View() tea.View {
	view := tea.NewView("")
	view.AltScreen = true
	view.BackgroundColor = blue
	view.ForegroundColor = white
	view.WindowTitle = "Brunel | Go TUI experiment"
	view.MouseMode = tea.MouseModeCellMotion
	if m.width < 40 || m.height < 16 {
		view.SetContent(ansi.Truncate("Resize to at least 40 × 16. Ctrl+C quits.", max(0, m.width), ""))
		return view
	}
	if m.surface == workspaceSurface {
		view.WindowTitle = "Brunel | Workspace"
		view.SetContent(m.workspaceView())
		return view
	}
	width := m.width - 4
	brand := mark.Render(" brunel ") + muted.Render("  / ") + strong.Render(filepath.Base(m.project))
	header := spread(brand, caution.Render("Simulated session"), width) + "\n" +
		muted.Render(ansi.Truncate(m.project, width, "…")) + "\n" +
		muted.Render(strings.Repeat("─", width))
	body := m.transcript.View()
	if m.width >= 110 {
		divider := muted.Render(strings.TrimSuffix(strings.Repeat(" │ \n", m.transcript.Height()), "\n"))
		body = lipgloss.JoinHorizontal(lipgloss.Top, body, divider, m.sidebar())
	}
	status := m.notice
	if status == "" {
		status = "Ready. Enter a prompt to try the demo."
	}
	if m.active != nil && m.notice == "" {
		status = "● Working. Esc stops the simulated run."
	}
	if !m.transcript.AtBottom() {
		status = "History paused. Ctrl+End returns to live output."
	}
	status = muted.Render(ansi.Truncate(status, width, "…"))
	composer := m.optionsRow(width) + "\n" + m.composer.View()
	help := "enter send · alt+enter newline · tab transcript · f2 settings · ^c quit"
	if m.canOpenWorkspace() {
		help = "← workspace · enter send · tab transcript · f2 settings · ^c quit"
	}
	if m.focus == transcriptFocus {
		escape := "esc message"
		if m.active != nil {
			escape = "esc stop"
		}
		help = "↑↓ select · enter details · pgup pgdn scroll · tab settings · " + escape + " · ^c quit"
	} else if m.focus == settingsFocus {
		help = "←→ field · ↑↓ value · enter cycle · esc message · ^c quit"
	}
	if width < 76 {
		help = "enter send · f2 settings · ^c quit"
		if m.canOpenWorkspace() {
			help = "← workspace · enter send · ^c quit"
		}
		if m.focus == transcriptFocus {
			help = "↑↓ select · enter open · tab · ^c quit"
		} else if m.focus == settingsFocus {
			help = "←→ field · ↑↓ value · esc · ^c quit"
		}
	}
	footer := muted.Render(ansi.Truncate(help, width, ""))
	content := strings.Join([]string{header, body, status, composer, footer}, "\n")
	view.SetContent(lipgloss.NewStyle().Padding(1, 2).Render(content))
	return view
}

func (m *model) optionsRow(width int) string {
	fields := []string{
		"model " + m.session.modelName + " ▾",
		"effort " + m.session.effort + " ▾",
		"machine local",
		"branch " + m.session.branch,
	}
	if ansi.StringWidth(strings.Join(fields, " · ")) > width {
		fields = []string{m.session.modelName, m.session.effort, "local", m.session.branch}
	}
	used := ansi.StringWidth(strings.Join(fields[:3], " · ")) + 3
	fields[3] = ansi.Truncate(fields[3], max(1, width-used), "…")
	for i := range fields {
		if i < 2 && m.focus == settingsFocus && m.setting == i {
			fields[i] = mark.Render(fields[i])
		} else {
			fields[i] = muted.Render(fields[i])
		}
	}
	row := strings.Join(fields, muted.Render(" · "))
	if remaining := width - lipgloss.Width(row); remaining > 1 {
		row += muted.Render(" " + strings.Repeat("─", remaining-1))
	}
	return row
}

func (m *model) transcriptContent() string {
	if len(m.entries) == 0 {
		return "\n" + strong.Render("Start with a small conversation.") + "\n\n" +
			muted.Render(ansi.Wrap("Enter a prompt to play a simulated run with streamed text, tool output, and two child agents. No model calls or repository actions are performed.", m.transcriptWidth(), "")) +
			"\n\n" + muted.Render("Try scrolling, expanding details, and stopping a run.")
	}
	blocks := make([]string, len(m.entries))
	for i, e := range m.entries {
		blocks[i] = m.renderEntry(e, i)
	}
	return strings.Join(blocks, "\n\n")
}

func (m *model) renderEntry(e entry, index int) string {
	width := m.transcriptWidth()
	if !e.expandable() {
		label := strong.Render(e.title)
		if e.kind == userEntry {
			label = mark.Render(" You ")
		}
		return label + "\n" + ink.Render(ansi.Wrap(e.text, width, ""))
	}
	prefix := "› "
	if e.expanded {
		prefix = "⌄ "
	}
	if e.kind == agentEntry {
		prefix += "Agent · "
	}
	title := prefix + e.title
	label := muted.Render(ansi.Truncate(title, max(1, width-13), "…"))
	if index == m.selected && m.focus == transcriptFocus {
		label = mark.Render(ansi.Truncate(title, max(1, width-13), "…"))
	}
	state := muted.Render(string(e.status))
	if e.status == running || e.status == cancelled {
		state = caution.Render(string(e.status))
	}
	block := spread(label, state, width) + "\n" + muted.Render(ansi.Wrap(e.text, width, ""))
	if e.expanded {
		detail := ansi.Wrap(e.details, max(1, width-4), "")
		block += "\n" + muted.Render("  │ "+strings.ReplaceAll(detail, "\n", "\n  │ "))
	}
	return block
}

func (m *model) entryLine(index int) int {
	line := 0
	for i := 0; i < index; i++ {
		line += lipgloss.Height(m.renderEntry(m.entries[i], i)) + 1
	}
	return line
}

func (m *model) sidebar() string {
	lines := []string{strong.Render("Session"), "", caution.Render("Demo runner"), muted.Render("No model connected"), "", strong.Render("Agents"), ""}
	count := 0
	for _, e := range m.entries {
		if e.runID == m.generation && e.kind == agentEntry {
			count++
			lines = append(lines, ink.Render(e.title), muted.Render("  "+string(e.status)), "")
		}
	}
	if count == 0 {
		lines = append(lines, muted.Render("No agents yet."), "")
	}
	lines = append(lines, strong.Render("Local experiment"), "", muted.Render("Go + Bubble Tea"), muted.Render("In-memory history"), "", muted.Render("All activity is simulated."))
	return lipgloss.NewStyle().Width(28).Height(m.transcript.Height()).MaxHeight(m.transcript.Height()).Render(strings.Join(lines, "\n"))
}

func spread(left, right string, width int) string {
	left = ansi.Truncate(left, max(0, width-lipgloss.Width(right)-1), "…")
	gap := max(1, width-lipgloss.Width(left)-lipgloss.Width(right))
	return ansi.Truncate(fmt.Sprintf("%s%s%s", left, strings.Repeat(" ", gap), right), width, "")
}
