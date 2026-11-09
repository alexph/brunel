package main

import (
	"os"
	"os/exec"
	"strings"
	"testing"
)

func TestBranchContextHandlesNamedDetachedAndNonGitDirectories(t *testing.T) {
	project := t.TempDir()
	git := func(args ...string) string {
		t.Helper()
		cmd := exec.Command("git", append([]string{"-C", project}, args...)...)
		cmd.Env = append(os.Environ(), "GIT_CONFIG_NOSYSTEM=1", "GIT_CONFIG_GLOBAL=/dev/null")
		output, err := cmd.CombinedOutput()
		if err != nil {
			t.Fatalf("git fixture failed: %v\n%s", err, output)
		}
		return strings.TrimSpace(string(output))
	}
	git("init", "--quiet", "-b", "topic/composer")
	if got := loadBranch(project)(); got != branchMsg("topic/composer") {
		t.Fatalf("named branch = %q", got)
	}
	git("-c", "user.name=Brunel Test", "-c", "user.email=brunel@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "--quiet", "--allow-empty", "-m", "fixture")
	git("checkout", "--quiet", "--detach")
	commit := git("rev-parse", "--short", "HEAD")
	if got := loadBranch(project)(); got != branchMsg("detached "+commit) {
		t.Fatalf("detached context = %q", got)
	}
	if got := loadBranch(t.TempDir())(); got != branchMsg("unavailable") {
		t.Fatalf("non-git context = %q", got)
	}
}
