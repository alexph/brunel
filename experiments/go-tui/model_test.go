package main

import (
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/ansi"
)

func testModel(width, height int) *model {
	m := newModel("/Users/alex/Projects/brunel")
	m.Update(tea.WindowSizeMsg{Width: width, Height: height})
	return m
}

func press(m *model, code rune, mod tea.KeyMod) tea.Cmd {
	_, cmd := m.Update(tea.KeyPressMsg{Code: code, Mod: mod})
	return cmd
}

func sendPrompt(m *model, text string) tea.Cmd {
	m.Update(tea.PasteMsg{Content: text})
	return press(m, tea.KeyEnter, 0)
}

func advanceDemo(m *model) {
	run := m.active
	m.Update(demoMsg{runID: run.id, step: run.next, event: run.steps[run.next].event})
}

func finishDemo(m *model) {
	for m.active != nil {
		advanceDemo(m)
	}
}

func TestConversationKeepsDraftAndExpandedDetailsDuringStreaming(t *testing.T) {
	m := testModel(120, 40)
	cmd := sendPrompt(m, "Explore the UI\nKeep it readable.")
	if cmd == nil || !strings.Contains(m.transcript.GetContent(), "Keep it readable.") {
		t.Fatal("Enter must submit the multiline prompt and schedule the demo")
	}
	// Exercise the real scheduled command once. Later steps bypass only the clock.
	m.Update(cmd())
	advanceDemo(m)
	advanceDemo(m)
	press(m, 'o', tea.ModCtrl)
	if !strings.Contains(m.transcript.GetContent(), "No file is opened.") {
		t.Fatal("Ctrl+O must expand the tool output")
	}
	m.Update(tea.PasteMsg{Content: "q is ordinary input"})
	press(m, tea.KeyEnter, tea.ModAlt)
	m.Update(tea.PasteMsg{Content: "second line"})
	if cmd := press(m, tea.KeyEnter, 0); cmd != nil {
		t.Fatal("Enter during a run must not start another run")
	}
	finishDemo(m)
	content := m.transcript.GetContent()
	for _, want := range []string{"Fixture output.", "Scout", "Reviewer", "The activity above is scripted."} {
		if !strings.Contains(ansi.Strip(content), want) {
			t.Errorf("completed transcript does not contain %q", want)
		}
	}
	if got := m.composer.Value(); got != "q is ordinary input\nsecond line" {
		t.Fatalf("draft changed during streaming: %q", got)
	}
	if m.entries[2].status != complete || !m.entries[2].expanded {
		t.Fatal("tool completion must preserve expanded details")
	}
}

func TestCancelledAndOutOfOrderEventsCannotChangeNewRun(t *testing.T) {
	m := testModel(80, 24)
	sendPrompt(m, "First run")
	advanceDemo(m)
	stale := demoMsg{runID: m.active.id, step: m.active.next, event: m.active.steps[m.active.next].event}
	press(m, tea.KeyEscape, 0)
	if m.active != nil || !strings.Contains(ansi.Strip(m.View().Content), "Stopped.") {
		t.Fatal("Escape must stop the run and show the result")
	}
	sendPrompt(m, "Second run")
	before := m.transcript.GetContent()
	m.Update(stale)
	m.Update(demoMsg{runID: m.active.id, step: 2, event: textDelta{"intro", "out of order"}})
	if got := m.transcript.GetContent(); got != before {
		t.Fatal("late or out-of-order output changed the new conversation")
	}
	advanceDemo(m)
	finishDemo(m)
	if strings.Count(ansi.Strip(m.transcript.GetContent()), "This is the whole experiment:") != 1 {
		t.Fatal("only the second run may finish its answer")
	}
}

func TestTypedDraftCanExceedTheVisibleComposerHeight(t *testing.T) {
	m := testModel(80, 24)
	for i, line := range []string{"one", "two", "three", "four", "five"} {
		if i > 0 {
			press(m, tea.KeyEnter, tea.ModAlt)
		}
		m.Update(tea.PasteMsg{Content: line})
	}
	press(m, tea.KeyEnter, 0)
	lines := strings.Split(ansi.Strip(m.transcript.GetContent()), "\n")
	for i := range lines {
		lines[i] = strings.TrimRight(lines[i], " ")
	}
	if !strings.Contains(strings.Join(lines, "\n"), "one\ntwo\nthree\nfour\nfive") {
		t.Fatalf("typed newlines were lost after the third line: %q", lines)
	}
}

func TestOpeningDetailsBringsTheBodyIntoView(t *testing.T) {
	m := testModel(40, 16)
	sendPrompt(m, "Show tool output")
	for range 3 {
		advanceDemo(m)
	}
	press(m, tea.KeyTab, 0)
	press(m, tea.KeyEnter, 0)
	if !strings.Contains(ansi.Strip(m.transcript.View()), "opened.") {
		t.Fatal("expanding a tool at the bottom left its details below the viewport")
	}
}

func TestScrollingPausesFollowWithoutLosingDraft(t *testing.T) {
	m := testModel(80, 24)
	sendPrompt(m, "Show the demo")
	for range 9 {
		advanceDemo(m)
	}
	m.Update(tea.PasteMsg{Content: "A draft while I read"})
	press(m, tea.KeyPgUp, 0)
	offset := m.transcript.YOffset()
	if m.transcript.AtBottom() {
		t.Fatal("Page Up must leave live output")
	}
	for range 15 {
		advanceDemo(m)
	}
	if m.transcript.YOffset() != offset || m.composer.Value() != "A draft while I read" {
		t.Fatal("new output moved the reader or changed the draft")
	}
	if !strings.Contains(ansi.Strip(m.View().Content), "History paused.") {
		t.Fatal("paused follow mode must be visible")
	}
	press(m, tea.KeyEnd, tea.ModCtrl)
	advanceDemo(m)
	if !m.transcript.AtBottom() {
		t.Fatal("Ctrl+End must resume following new output")
	}
}

func TestViewsFitAndDetailsRemainReachableAcrossResize(t *testing.T) {
	m := testModel(120, 40)
	m.project = "/Users/alex/Projects/" + strings.Repeat("long", 20)
	sendPrompt(m, "Review 界面 🛠 "+strings.Repeat("long_path_", 35))
	finishDemo(m)
	press(m, tea.KeyTab, 0)
	press(m, tea.KeyUp, 0)
	press(m, tea.KeyEnter, 0)
	for _, size := range [][2]int{{144, 48}, {110, 32}, {80, 24}, {40, 16}, {20, 8}, {120, 40}} {
		m.Update(tea.WindowSizeMsg{Width: size[0], Height: size[1]})
		content := m.View().Content
		lines := strings.Split(content, "\n")
		if len(lines) > size[1] {
			t.Errorf("%dx%d view has %d rows", size[0], size[1], len(lines))
		}
		for row, line := range lines {
			if width := ansi.StringWidth(line); width > size[0] {
				t.Errorf("%dx%d row %d has width %d", size[0], size[1], row, width)
			}
		}
		if size[0] >= 40 && !strings.Contains(ansi.Strip(m.transcript.GetContent()), "Simulated result.") {
			t.Errorf("%dx%d resize lost expanded agent details", size[0], size[1])
		}
		if size[0] >= 40 && !strings.Contains(ansi.Strip(content), "Simulated session") {
			t.Errorf("%dx%d long project name hid the demo label", size[0], size[1])
		}
	}
}

func TestHistoryRetainsTenWholeTurns(t *testing.T) {
	m := testModel(80, 24)
	for i := range 12 {
		sendPrompt(m, "Prompt "+string(rune('A'+i)))
		finishDemo(m)
	}
	content := ansi.Strip(m.transcript.GetContent())
	if strings.Contains(content, "Prompt A") || strings.Contains(content, "Prompt B") {
		t.Fatal("old turns were retained")
	}
	for _, want := range []string{"Prompt C", "Prompt L"} {
		if !strings.Contains(content, want) {
			t.Errorf("retained history is missing %q", want)
		}
	}
	if got := strings.Count(content, "This is the whole experiment:"); got != 10 {
		t.Fatalf("retained %d answers, want ten complete turns", got)
	}
}

func TestComposerGrowsUpwardAndShrinksWithoutDiscardingText(t *testing.T) {
	m := testModel(80, 30)
	initialTranscriptRows := m.transcript.Height()
	if m.composer.Height() != 1 {
		t.Fatal("an empty composer must occupy one row")
	}
	m.Update(tea.PasteMsg{Content: "one"})
	press(m, tea.KeyEnter, tea.ModAlt)
	m.Update(tea.PasteMsg{Content: "two"})
	if m.composer.Height() != 2 || m.transcript.Height() != initialTranscriptRows-1 {
		t.Fatal("the second input row must grow upward into the transcript")
	}
	m.Update(tea.PasteMsg{Content: strings.Repeat("\nmore", 12)})
	press(m, tea.KeyEnter, tea.ModAlt)
	m.Update(tea.PasteMsg{Content: "past the cap"})
	if m.composer.Height() != 8 || !strings.HasSuffix(m.composer.Value(), "\npast the cap") {
		t.Fatal("the visible cap must not limit the editable draft")
	}
	if !strings.Contains(ansi.Strip(m.composer.View()), "past the cap") {
		t.Fatal("the capped input must scroll to its cursor")
	}
	for range len([]rune(m.composer.Value())) {
		press(m, tea.KeyBackspace, 0)
	}
	if m.composer.Height() != 1 || m.transcript.Height() != initialTranscriptRows {
		t.Fatal("deleting the draft must return space to the transcript")
	}
	view := ansi.Strip(m.View().Content)
	if strings.ContainsAny(view, "╭╰╮╯") {
		t.Fatal("the composer must have no enclosing frame")
	}
	options := strings.Index(view, "model demo")
	input := strings.LastIndex(view, "› ")
	if options < 0 || input < options {
		t.Fatal("the options row must sit immediately above the input")
	}
}

func TestComposerGrowthIncludesSoftWrapAndResizesWithoutLosingDraft(t *testing.T) {
	m := testModel(80, 30)
	m.Update(tea.PasteMsg{Content: strings.Repeat("x", 75)})
	if m.composer.Height() != 2 {
		t.Fatalf("a wrapped input must grow to two rows, got %d", m.composer.Height())
	}
	m.Update(tea.WindowSizeMsg{Width: 120, Height: 30})
	if m.composer.Height() != 1 {
		t.Fatal("a wider terminal must shrink a draft that no longer wraps")
	}
	m.Update(tea.PasteMsg{Content: "\n" + strings.Repeat("界", 50) + "\nlast"})
	draft := m.composer.Value()
	m.Update(tea.WindowSizeMsg{Width: 40, Height: 16})
	if m.composer.Height() != 4 || m.transcript.Height() < 4 {
		t.Fatal("a short terminal must preserve four transcript rows")
	}
	if m.composer.Value() != draft {
		t.Fatal("resize changed the draft")
	}
	if lines := strings.Split(m.View().Content, "\n"); len(lines) != 16 {
		t.Fatalf("resized view uses %d rows, want 16", len(lines))
	}
	press(m, tea.KeyEnter, 0)
	if m.composer.Height() != 1 {
		t.Fatal("sending a draft must reset the composer to one row")
	}
}

func TestDemoSettingsHaveSeparateFocusAndPreserveDraft(t *testing.T) {
	m := testModel(120, 40)
	m.Update(branchMsg("topic/composer"))
	sendPrompt(m, "Show activity")
	for range 5 {
		advanceDemo(m)
	}
	m.Update(tea.PasteMsg{Content: "keep this draft"})
	press(m, tea.KeyTab, 0)
	if m.focus != transcriptFocus || m.selected < 0 {
		t.Fatal("the first Tab must still focus transcript activity")
	}
	press(m, tea.KeyF2, 0)
	press(m, tea.KeyEnter, 0)
	press(m, tea.KeyRight, 0)
	press(m, tea.KeyUp, 0)
	row := ansi.Strip(m.optionsRow(116))
	for _, want := range []string{"model demo-fast", "effort low", "machine local", "branch topic/composer"} {
		if !strings.Contains(row, want) {
			t.Errorf("settings row is missing %q", want)
		}
	}
	press(m, tea.KeyEscape, 0)
	if m.active == nil || m.focus != composerFocus || !m.composer.Focused() {
		t.Fatal("leaving settings must restore the composer without stopping the run")
	}
	if m.composer.Value() != "keep this draft" {
		t.Fatal("changing settings altered the draft")
	}
	press(m, tea.KeyTab, tea.ModShift)
	if m.focus != settingsFocus {
		t.Fatal("Shift+Tab from the composer must focus settings")
	}
	press(m, tea.KeyTab, 0)
	if m.focus != composerFocus {
		t.Fatal("Tab from settings must return to the composer")
	}
	press(m, tea.KeyTab, 0)
	if !strings.Contains(ansi.Strip(m.View().Content), "esc stop") {
		t.Fatal("transcript help must describe Escape cancelling an active run")
	}
	press(m, tea.KeyEscape, 0)
	if m.active != nil {
		t.Fatal("Escape from the transcript must match the stop hint")
	}
}

func TestComposerGrowthPreservesPausedTranscript(t *testing.T) {
	m := testModel(80, 24)
	sendPrompt(m, "Show a full turn")
	finishDemo(m)
	press(m, tea.KeyPgUp, 0)
	offset := m.transcript.YOffset()
	m.Update(tea.PasteMsg{Content: "one\ntwo\nthree\nfour"})
	if m.transcript.AtBottom() || m.transcript.YOffset() != offset {
		t.Fatal("composer growth must not resume following or move the reader")
	}
}
