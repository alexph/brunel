package main

import (
	"strings"

	"charm.land/bubbles/v2/key"
	"charm.land/bubbles/v2/textarea"
	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"
)

type entryKind int

const (
	userEntry entryKind = iota
	assistantEntry
	toolEntry
	agentEntry
)

type entryStatus string

const (
	running   entryStatus = "working"
	complete  entryStatus = "complete"
	cancelled entryStatus = "stopped"
)

type entry struct {
	runID    uint64
	id       string
	kind     entryKind
	title    string
	text     string
	details  string
	status   entryStatus
	expanded bool
}

func (e entry) expandable() bool {
	return e.kind == toolEntry || e.kind == agentEntry
}

type demoRun struct {
	id    uint64
	next  int
	steps []demoStep
}

type focusArea int

const (
	composerFocus focusArea = iota
	transcriptFocus
	settingsFocus
)

const (
	maxComposerRows   = 8
	fixedLayoutRows   = 8
	minTranscriptRows = 4
)

type model struct {
	project    string
	width      int
	height     int
	composer   textarea.Model
	transcript viewport.Model
	entries    []entry
	active     *demoRun
	generation uint64
	selected   int
	notice     string
	focus      focusArea
	setting    int
	session    sessionOptions
	surface    surface
	workspace  workspaceState
	lastResult entryStatus
}

func newModel(project string) *model {
	input := textarea.New()
	input.Placeholder = "Try: explore a small Go TUI"
	input.Prompt = "› "
	input.ShowLineNumbers = false
	input.CharLimit = 4096
	input.DynamicHeight = true
	input.MinHeight = 1
	input.MaxHeight = maxComposerRows
	// Keep the visible row cap separate from the draft's content limit.
	input.MaxContentHeight = input.CharLimit + 1
	input.MaxWidth = 0
	input.SetHeight(1)
	input.SetPromptFunc(2, func(info textarea.PromptInfo) string {
		if info.LineNumber == 0 {
			return "› "
		}
		return "  "
	})
	input.KeyMap.InsertNewline = key.NewBinding(key.WithKeys("alt+enter", "shift+enter", "ctrl+j"))
	input.SetStyles(composerStyles())
	input.Focus()
	return &model{
		project: project, composer: input, transcript: viewport.New(), selected: -1,
		session:   sessionOptions{modelName: "demo", effort: "medium", branch: "…"},
		workspace: workspaceState{list: viewport.New(), details: viewport.New()},
	}
}

func (m *model) Init() tea.Cmd {
	return tea.Batch(textarea.Blink, loadBranch(m.project))
}

func (m *model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.resize(msg.Width, msg.Height)
		if m.surface == workspaceSurface {
			m.updateWorkspace(false)
		}
		return m, nil
	case branchMsg:
		m.session.branch = string(msg)
		if m.surface == workspaceSurface {
			m.updateWorkspace(false)
		}
		return m, nil
	case demoMsg:
		// A cancelled run can leave one timer in flight. It cannot update a new run.
		if m.active == nil || msg.runID != m.active.id || msg.step != m.active.next {
			return m, nil
		}
		follow := m.transcript.AtBottom()
		m.applyDemo(msg.event)
		m.refreshTranscript(follow)
		if m.surface == workspaceSurface {
			m.updateWorkspace(false)
		}
		if m.active == nil {
			return m, nil
		}
		m.active.next++
		return m, nextDemoStep(*m.active)
	case tea.KeyPressMsg:
		if msg.String() == "ctrl+c" {
			return m, tea.Quit
		}
		if m.surface == workspaceSurface {
			return m, m.updateWorkspaceKey(msg)
		}
		if msg.String() == "left" && m.canOpenWorkspace() {
			m.surface = workspaceSurface
			m.composer.Blur()
			m.updateWorkspace(true)
			return m, nil
		}
		switch msg.String() {
		case "esc":
			if m.active != nil && m.focus != settingsFocus {
				m.stopRun()
			}
			return m, m.setFocus(composerFocus)
		case "tab":
			return m, m.setFocus((m.focus + 1) % 3)
		case "shift+tab":
			return m, m.setFocus((m.focus + 2) % 3)
		case "f2":
			return m, m.setFocus(settingsFocus)
		case "pgup":
			m.transcript.PageUp()
			return m, nil
		case "pgdown":
			m.transcript.PageDown()
			return m, nil
		case "ctrl+end":
			m.transcript.GotoBottom()
			return m, nil
		case "ctrl+o":
			if m.selected < 0 {
				m.selectDetail(-1)
			}
			m.toggleDetails()
			return m, nil
		case "enter":
			switch m.focus {
			case composerFocus:
				return m, m.submit()
			case settingsFocus:
				m.cycleSetting(1)
			default:
				m.toggleDetails()
			}
			return m, nil
		}
		if m.focus == settingsFocus {
			switch msg.String() {
			case "left", "right":
				m.setting = (m.setting + 1) % 2
			case "up":
				m.cycleSetting(-1)
			case "down", "space":
				m.cycleSetting(1)
			}
			return m, nil
		}
		if m.focus == transcriptFocus {
			switch msg.String() {
			case "up", "k":
				m.selectDetail(-1)
			case "down", "j":
				m.selectDetail(1)
			case "home":
				m.transcript.GotoTop()
			case "end":
				m.transcript.GotoBottom()
			}
			return m, nil
		}
	case tea.MouseWheelMsg:
		var cmd tea.Cmd
		if m.surface == workspaceSurface {
			m.workspace.details, cmd = m.workspace.details.Update(msg)
			return m, cmd
		}
		m.transcript, cmd = m.transcript.Update(msg)
		return m, cmd
	}
	if m.surface == workspaceSurface {
		return m, nil
	}
	follow := m.transcript.AtBottom()
	previousHeight := m.composer.Height()
	var cmd tea.Cmd
	m.composer, cmd = m.composer.Update(msg)
	if m.composer.Height() != previousHeight {
		m.layoutTranscript(follow)
	}
	return m, cmd
}

func (m *model) setFocus(area focusArea) tea.Cmd {
	m.focus = area
	if area == composerFocus {
		m.refreshTranscript(false)
		return m.composer.Focus()
	}
	m.composer.Blur()
	if area == transcriptFocus && m.selected < 0 {
		m.selectDetail(-1)
	}
	m.refreshTranscript(false)
	return nil
}

func (m *model) submit() tea.Cmd {
	prompt := strings.TrimSpace(m.composer.Value())
	if prompt == "" {
		return nil
	}
	if m.active != nil {
		m.notice = "Esc stops the current run. Your next draft stays here."
		return nil
	}
	m.generation++
	// Retain whole turns, with at most ten scripted turns in memory.
	first := 0
	for first < len(m.entries) && m.entries[first].runID+10 <= m.generation {
		first++
	}
	m.entries = append([]entry(nil), m.entries[first:]...)
	m.entries = append(m.entries, entry{
		runID: m.generation, id: "user", kind: userEntry,
		title: "You", text: prompt, status: complete,
	})
	m.selected = -1
	m.notice = ""
	m.composer.Reset()
	m.active = &demoRun{id: m.generation, steps: demoScript()}
	m.layoutTranscript(true)
	return nextDemoStep(*m.active)
}

func (m *model) stopRun() {
	for i := range m.entries {
		if m.entries[i].runID == m.active.id && m.entries[i].status == running {
			m.entries[i].status = cancelled
		}
	}
	m.active = nil
	m.lastResult = cancelled
	m.notice = "Stopped. Partial output is kept."
	m.refreshTranscript(m.transcript.AtBottom())
}

func (m *model) selectDetail(direction int) {
	start := m.selected + direction
	if m.selected < 0 {
		start = len(m.entries) - 1
	}
	for i := start; i >= 0 && i < len(m.entries); i += direction {
		if m.entries[i].expandable() {
			m.selected = i
			m.refreshTranscript(false)
			m.transcript.SetYOffset(m.entryLine(i))
			return
		}
	}
}

func (m *model) toggleDetails() {
	if m.selected < 0 || m.selected >= len(m.entries) {
		return
	}
	m.entries[m.selected].expanded = !m.entries[m.selected].expanded
	m.refreshTranscript(false)
	if m.entries[m.selected].expanded {
		m.transcript.SetYOffset(m.entryLine(m.selected))
	}
}

func (m *model) resize(width, height int) {
	follow := m.transcript.AtBottom()
	m.width, m.height = width, height
	m.composer.MaxHeight = min(maxComposerRows, max(1, height-fixedLayoutRows-minTranscriptRows))
	m.composer.SetWidth(max(1, width-4))
	m.layoutTranscript(follow)
}

func (m *model) layoutTranscript(follow bool) {
	m.transcript.SetWidth(m.transcriptWidth())
	m.transcript.SetHeight(max(1, m.height-fixedLayoutRows-m.composer.Height()))
	m.refreshTranscript(follow)
}

func (m *model) refreshTranscript(follow bool) {
	m.transcript.SetContent(m.transcriptContent())
	if follow {
		m.transcript.GotoBottom()
	}
}
