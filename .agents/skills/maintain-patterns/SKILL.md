---
name: maintain-patterns
description: Create, update, and organize repository coding conventions in .agents/patterns/ and its index. Use when asked to capture a coding decision as a pattern, revise rules, or reconcile patterns with repository evidence. Ordinary coding, refactoring, and code review do not by themselves request pattern maintenance.
---

# Maintain patterns

Maintain actionable repository conventions in `.agents/patterns/`. Read the index and relevant pattern files before changing them, and inspect representative code when needed to understand the convention or check an example.

## Establish the rule

Use the user's stated decisions and existing documented rules as policy. Existing code provides evidence and examples; repetition alone does not make an implementation choice a requirement. If a consequential policy choice is unresolved, ask a focused question or clearly present it as a proposal rather than recording it as established policy.

When code conflicts with a documented rule, report the discrepancy. Do not silently change the rule to match the code. Check whether the user intends to change policy, document a scoped exception, or leave the code for a later refactor.

## Write grouped pattern files

Group related rules by the work they guide, such as writing tests, code style, or backend actions and readers. Prefer updating a relevant file over creating many small files. Split a file when its rules have meaningfully different scopes or it becomes difficult to navigate.

Give each rule a descriptive heading and state what decision it changes. Distinguish requirements from preferences. Use conditional wording such as “Given …, …” when the rule depends on a specific situation. Include the reason, known exceptions, and concise do/avoid code samples when they clarify application; omit sections that add no useful information. Do not invent exceptions or require a rigid template.

Keep examples consistent with the intended policy and relevant repository APIs. Label hypothetical examples and existing deviations accurately. Prefer a short self-contained example; link to representative code when that helps explain context. Avoid duplicating rules across files or copying general advice that adds no repository-specific guidance.

## Maintain the index

Keep `.agents/patterns/index.md` as the entry point. Organize it with descriptive H2 groups for readability, each containing a table with `Patterns` and `Read when` columns. Link each pattern file with a relative Markdown link and give it a direct trigger sentence, such as “Read before writing or updating tests.”

Triggers should cover the rules in the linked file and let an agent decide applicability before editing code. Multiple rows may apply to one task. Reorganize groups as the library grows; headings do not require matching directories. Index each pattern file once, and update links and triggers when files move, merge, or change scope. Do not add empty groups or links to files that do not exist.

## Finish

Check that index links resolve, triggers match their files, and the changed rules have no unresolved contradictions or duplicated requirements. Summarize the policy changes and any remaining uncertainty.

Pattern maintenance changes the documents. It does not by itself authorize refactoring application code. When separately requested, implementation work can apply these patterns alongside bench-mode or another coding workflow.
