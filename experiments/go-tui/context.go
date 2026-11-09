package main

import (
	"context"
	"os/exec"
	"slices"
	"strings"
	"time"

	tea "charm.land/bubbletea/v2"
)

type sessionOptions struct {
	modelName string
	effort    string
	branch    string
}

type branchMsg string

func loadBranch(project string) tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), time.Second)
		defer cancel()
		branch, err := exec.CommandContext(ctx, "git", "-C", project, "symbolic-ref", "--quiet", "--short", "HEAD").Output()
		if err == nil {
			return branchMsg(strings.TrimSpace(string(branch)))
		}
		commit, err := exec.CommandContext(ctx, "git", "-C", project, "rev-parse", "--short", "HEAD").Output()
		if err == nil {
			return branchMsg("detached " + strings.TrimSpace(string(commit)))
		}
		return branchMsg("unavailable")
	}
}

func (m *model) cycleSetting(direction int) {
	choices := []string{"demo", "demo-fast", "demo-deep"}
	value := &m.session.modelName
	if m.setting == 1 {
		choices = []string{"low", "medium", "high"}
		value = &m.session.effort
	}
	index := slices.Index(choices, *value)
	*value = choices[(index+direction+len(choices))%len(choices)]
	m.notice = "Demo settings only. Output remains scripted."
}
