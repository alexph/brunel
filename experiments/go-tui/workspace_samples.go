package main

func workspaceSamples(tab workspaceTab) []workspaceRow {
	switch tab {
	case threadsTab:
		return []workspaceRow{
			{title: "Define the issue ingestion boundary", status: "Ready", summary: "brunel · local · sample thread", details: "Sample thread\n\nProject\nbrunel\n\nSubject\nPull an issue into a conversation while retaining its tracker reference.\n\nLatest message\nKeep the imported issue as context. Let the thread hold the discussion and work history.\n\nThis row has no stored messages or live agent. Issue ingestion is not connected."},
			{title: "Review a workflow waiting for input", status: "Needs input", summary: "relay · build-node · sample thread", details: "Sample thread\n\nProject\nrelay\n\nMachine\nbuild-node (example)\n\nPrompt\nWhich dependency should unblock the next workflow step?\n\nThis is a layout preview. No DAG scheduler, remote machine, or pending approval exists."},
			{title: "Explore durable conversation history", status: "Idle", summary: "brunel · local · sample thread", details: "Sample thread\n\nProject\nbrunel\n\nSubject\nRetain messages and tool results across restarts.\n\nLatest message\nStart with the storage contract before choosing a representation.\n\nThis thread is example content. The Go prototype has no durable message storage."},
			{title: "Check a remote agent's progress", status: "Working", summary: "workbench · lab-01 · sample thread", details: "Sample thread\n\nMachine\nlab-01 (example)\n\nActivity\nInspecting a repository.\n\nThe working state is sample data. There is no remote connection or background agent behind this row."},
		}
	case projectsTab:
		return []workspaceRow{
			{title: "relay", status: "Sample", summary: "Example project · build-node", details: "Sample project\n\nName\nrelay\n\nMachine\nbuild-node (example)\n\nThreads\nOne example thread awaiting input.\n\nThis project is sample data. No directory is registered or opened."},
			{title: "workbench", status: "Sample", summary: "Example project · lab-01", details: "Sample project\n\nName\nworkbench\n\nMachine\nlab-01 (example)\n\nThreads\nOne example thread marked working.\n\nThis project is sample data. No directory is registered or opened."},
		}
	case issuesTab:
		return []workspaceRow{
			{title: "EX-12  Import issues into project threads", status: "Open", summary: "brunel · example issue · no tracker connected", details: "Sample issue\n\nReference\nEX-12\n\nProject\nbrunel\n\nDescription\nBring an issue's title, description, and source identity into a conversation.\n\nDiscussion\nA linked thread can retain questions and implementation work.\n\nThis reference is invented for the preview. No issue API has been called."},
			{title: "EX-18  Keep messages across restarts", status: "Triage", summary: "brunel · example issue", details: "Sample issue\n\nReference\nEX-18\n\nProject\nbrunel\n\nDescription\nPersist conversation messages and tool activity.\n\nThis is example content. No issue or stored thread exists behind the row."},
			{title: "EX-24  Resume work on another machine", status: "Later", summary: "relay · example issue", details: "Sample issue\n\nReference\nEX-24\n\nProject\nrelay\n\nDescription\nReconnect a thread to an agent executing remotely.\n\nRemote agents are a future capability. This row does not connect to a machine."},
		}
	case machinesTab:
		return []workspaceRow{
			{title: "build-node", status: "Available", summary: "Example machine · Linux · no connection", details: "Sample machine\n\nName\nbuild-node\n\nPlatform\nLinux (example)\n\nPurpose\nRun longer project workflows.\n\nThe available state is example data. No machine is registered, contacted, or authenticated."},
			{title: "lab-01", status: "Offline", summary: "Example machine · macOS · no connection", details: "Sample machine\n\nName\nlab-01\n\nPlatform\nmacOS (example)\n\nPurpose\nRun an agent alongside a local development environment.\n\nThe offline state is example data. No connectivity check has been performed."},
		}
	}
	return nil
}
