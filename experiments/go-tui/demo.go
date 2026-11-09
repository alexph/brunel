package main

import (
	"strings"
	"time"

	tea "charm.land/bubbletea/v2"
)

type textDelta struct{ id, text string }
type runFinished struct{}

type demoStep struct {
	after time.Duration
	event tea.Msg
}

type demoMsg struct {
	runID uint64
	step  int
	event tea.Msg
}

func nextDemoStep(run demoRun) tea.Cmd {
	if run.next >= len(run.steps) {
		return nil
	}
	step := run.steps[run.next]
	return tea.Tick(step.after, func(time.Time) tea.Msg {
		return demoMsg{runID: run.id, step: run.next, event: step.event}
	})
}

func (m *model) applyDemo(event tea.Msg) {
	switch event := event.(type) {
	case entry:
		event.runID = m.active.id
		for i, previous := range m.entries {
			if previous.runID == event.runID && previous.id == event.id {
				event.expanded = previous.expanded
				m.entries[i] = event
				return
			}
		}
		m.entries = append(m.entries, event)
	case textDelta:
		for i := range m.entries {
			if m.entries[i].runID == m.active.id && m.entries[i].id == event.id {
				m.entries[i].text += event.text
				return
			}
		}
	case runFinished:
		for i := range m.entries {
			if m.entries[i].runID == m.active.id && m.entries[i].status == running {
				m.entries[i].status = complete
			}
		}
		m.active = nil
		m.lastResult = complete
		m.notice = "Demo complete. Send another prompt to replay."
	}
}

func demoScript() []demoStep {
	steps := []demoStep{
		{200 * time.Millisecond, entry{
			id: "intro", kind: assistantEntry, title: "Brunel", status: running,
			text: "Let's try a small conversation interface. ",
		}},
		{350 * time.Millisecond, textDelta{"intro", "I'll show tool output and two child agents while you keep using the composer."}},
		{400 * time.Millisecond, entry{
			id: "read", kind: toolEntry, title: "Read project notes", status: running,
			text:    "Preparing fixture output",
			details: "This tool is simulated. No file is opened.",
		}},
		{500 * time.Millisecond, entry{
			id: "scout", kind: agentEntry, title: "Scout", status: running,
			text:    "Explore the conversation layout",
			details: "Simulated child agent.\nTask: find the smallest useful conversation screen.\nExample skill context: bench-mode.\nNo skill file is loaded or executed by this demo.",
		}},
		{500 * time.Millisecond, entry{
			id: "reviewer", kind: agentEntry, title: "Reviewer", status: running,
			text:    "Check cancellation and keyboard behavior",
			details: "Simulated child agent.\nTask: challenge focus, cancellation, scrolling, and resize behavior.\nExample skill context: bench-mode.\nNo agent process is running.",
		}},
		{500 * time.Millisecond, entry{
			id: "read", kind: toolEntry, title: "Read project notes", status: complete,
			text:    "Fixture ready. Expand to inspect.",
			details: "Fixture output. No repository action was performed.\n\nConversation screen\n  Transcript keeps partial messages.\n  Tool output stays collapsed until requested.\n  Child agents report work in the same timeline.\n  The composer remains editable during a run.\n  Cancellation keeps completed and partial output.\n  A stale event cannot enter a later run.\n  Page Up leaves live-follow mode.\n  Ctrl+End returns to the latest output.\n  Narrow windows keep activity in the transcript.\n  History keeps the ten most recent demo turns.",
		}},
		{650 * time.Millisecond, entry{
			id: "scout", kind: agentEntry, title: "Scout", status: complete,
			text:    "One transcript. One composer. Details on demand.",
			details: "Simulated result.\nKeep the conversation as the main surface.\nUse a narrow activity pane only when there is room.\nKeep tool and agent details in the transcript at every width.",
		}},
		{650 * time.Millisecond, entry{
			id: "reviewer", kind: agentEntry, title: "Reviewer", status: complete,
			text:    "Keep typing, stop a run, then start another.",
			details: "Simulated result, not an executed test report.\nA stopped timer must not update the next run.\nTyping during a run must preserve the draft.\nNew output must not pull a reader back to the bottom.\nResize and detail expansion must keep the screen usable.",
		}},
		{250 * time.Millisecond, entry{
			id: "answer", kind: assistantEntry, title: "Brunel", status: running,
		}},
	}
	answer := "This is the whole experiment: a readable event loop, a scrollable transcript, and a composer that stays yours.\n\nUse Tab to focus the transcript, then the arrow keys to select a tool or agent. Enter expands its details. Page Up scrolls without interrupting your draft.\n\nThe activity above is scripted. There is no model connection, real delegation, skill execution, or file access. The next decision is whether this interface feels worth building on."
	for _, word := range strings.SplitAfter(answer, " ") {
		steps = append(steps, demoStep{45 * time.Millisecond, textDelta{"answer", word}})
	}
	return append(steps, demoStep{150 * time.Millisecond, runFinished{}})
}
