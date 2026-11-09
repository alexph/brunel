package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	tea "charm.land/bubbletea/v2"
)

func main() {
	project := flag.String("project", ".", "Directory to display. The demo does not modify it.")
	flag.Parse()
	if flag.NArg() != 0 {
		fmt.Fprintln(os.Stderr, "Use -project PATH to select a directory.")
		os.Exit(2)
	}
	path, err := filepath.Abs(*project)
	if err == nil {
		var info os.FileInfo
		info, err = os.Stat(path)
		if err == nil && !info.IsDir() {
			err = fmt.Errorf("%s is not a directory", path)
		}
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if _, err = tea.NewProgram(newModel(path)).Run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
