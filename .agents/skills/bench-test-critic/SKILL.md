---
name: bench-test-critic
description: Critique whether tests protect observable behavior or pin implementation details. Use for test-quality reviews, keep-or-prune decisions, or /bench-test-critic. Defaults to the current diff unless the user names files, locations, commits, or a comparison.
disable-model-invocation: true
---

# Test critic

Review tests without changing them. Recommend what to keep, rewrite, or prune, with evidence and a readable report. Do not optimize for deleting tests or agreeing with the user's opinion.

Use the `bench-mode` skill and read [Test behavior, not implementation](../principle-test-behavior-not-implementation/SKILL.md) before judging tests. It owns the evaluation criteria and preservation rules. Apply [Seek evidence that could prove you wrong](../principle-seek-evidence-that-could-prove-you-wrong/SKILL.md) when choosing experiments. Apply [Prove your work](../principle-prove-your-work/SKILL.md) to verification claims. Follow [unslop](../unslop/SKILL.md) for the report.

## Select the scope

1. Honor explicit files, directories, symbols, line ranges, commits, or comparison references. For a named test file, review its tests even when the file is unchanged. For a production location, inspect tests of its affected behavior.
2. Otherwise, use the current working-tree changes relative to `HEAD`. Include staged and unstaged changes with `git diff --find-renames HEAD`. Include relevant untracked files from `git ls-files --others --exclude-standard`. Do not substitute a branch comparison or recent commits.
3. Review added and changed tests, removed regression cases, and existing tests of changed production behavior. Read companion tests and callers as context. Keep recommendations within the selected scope.
4. If no relevant tests or changed production behavior exist, report that result and stop. Do not invent a sample or broaden the review. Treat failed scope discovery as a failure, not an empty diff.

State the selected scope before a substantial review. Identify the base reference when applicable. Review every in-scope test. If the user requests a sample, identify the sample and what it excludes. Separate judgments on individual parameter cases when their behavior differs.

Do not edit tests, production code, skills, or documentation during the review. Do not stage or commit changes. A request to apply recommendations is separate work.

## Establish each test's claim

Read the test, its fixtures, the exercised implementation, and the nearest caller. Identify:

- The consumer and the concrete result, error, state, or external effect promised to that consumer.
- The input and scenario the test actually exercises.
- Which boundary is real and which behavior is replaced by fixtures or mocks.
- The useful protection supplied by companion tests.

Do not derive a requirement solely from a test name or the current implementation. If a consequential contract remains unclear after inspection, mark the verdict unresolved and name the missing requirement.

For an internal call-order or request-state assertion, identify the consumer that relies on it. A test name alone does not establish that ordering or representation as a contract. Without supporting evidence, recommend assertion-only revision or mark the requirement unresolved.

Keep claims as narrow as the exercised inputs. Rejecting one invalid credential does not prove that every credential of that kind is rejected.

Apply the principle's two edits to that specific claim. Consider a fault in the promised behavior and an internal change that preserves it. Distinguish a brittle assertion from a useless test. Prefer removing an incidental assertion over discarding unique regression coverage.

Use these judgments:

- **Keep.** The test protects a demonstrated behavior or justified invariant without an identified implementation constraint.
- **Rewrite.** The scenario is valuable, but the boundary, setup, or assertions do not establish its claim cleanly. Name what to retain and what to change.
- **Prune.** The test or assertion adds no justified protection, or duplicates protection that an identified retained test supplies. Name the retained coverage or explain why no replacement is needed.
- **Unresolved.** Missing contract evidence or an execution limit prevents a defensible judgment. Name the missing evidence. Do not count this as keep or prune.

Do not use runtime pass or fail as a quality verdict. Do not require a deletion recommendation.

## Check for misleading evidence

- A surviving mutation is not an automatic prune. Check that the mutation breaks this test's claim and inspect companion coverage.
- An omission test can rely on a positive companion that proves the observation point can see the effect.
- A relational invariant can rely on separate tests for output correctness. A constant implementation passing the invariant alone does not establish redundancy.
- A mock is not automatically wrong. Distinguish an external boundary from an internal helper. Assert observable payloads or effects where practical.
- A mocked authorization policy cannot demonstrate real authorization. A mocked publisher cannot demonstrate message construction or delivery. Treat those as coverage limits unless the test claims to cover them.
- A request factory that assigns a user and invokes a resolved view does not exercise session-cookie loading or the full middleware chain.
- A prompt-layout test does not establish model behavior. A wording change is not proven behavior-preserving merely because it reads similarly.
- Separate per-route access guarantees from shared authentication logic. Shared machinery does not make route coverage redundant.

Ignore placement, naming, and style complaints unless they change the test's behavior, isolation, or maintenance cost. Do not turn the review into a general code audit.

## Exercise consequential judgments

Run the relevant existing tests as a baseline. Use the repository's normal runtime and test commands. Preserve and report existing failures. A failed baseline limits mutation conclusions but does not prevent independent inspection.

For consequential rewrite or prune recommendations, try the smallest practical experiment that could disprove the judgment. Use representative experiments rather than an exhaustive mutation matrix.

1. State the contract and expected result before the experiment.
2. Inject one relevant fault, such as a wrong result, omitted effect, duplicate effect, or weakened access check.
3. Where practical, try an internal change expected to preserve the contract.
4. Run the specific test and any companion needed to interpret its result.
5. Record the observed result and the assertion or behavior that detected the change.

Use isolated processes, in-memory patches, or a disposable copy. Do not mutate the user's working tree. Avoid real external effects. Remove temporary artifacts you create.

An import error, collection failure, or unrelated exception does not show that a test caught the intended fault. Label unexecuted edits as thought experiments. Label an unconfirmed behavior-preserving edit as an assumption. Do not claim a mutation experiment when only inspecting source.

After experiments, run the relevant unmodified tests if isolation or restoration is uncertain. Report execution blockers without converting them into quality failures. Do not add permanent tests or mutation infrastructure for the review.

## Write the report

Use compact Markdown with linked source locations. Use tables for comparisons. Avoid scores, decorative charts, and transcript dumps. Include only evidence gathered for this review.

Start with the recommendation and its consequence for consumers and maintainers. State the scope and whether files were changed. Then use this structure:

### Test judgments

| Test or assertion                                          | Verdict                              | Behavior protected and reason          | Recommended action                                                                 |
| ---------------------------------------------------------- | ------------------------------------ | -------------------------------------- | ---------------------------------------------------------------------------------- |
| Linked `path::test_name`, with parameter case when needed. | Keep, Rewrite, Prune, or Unresolved. | Concrete claim and evidence reference. | Specific retained coverage, replacement boundary, assertion removal, or no change. |

Give each test a row. Group parameter cases when their judgment and reason are the same. List the covered cases in that row rather than repeating identical rows. Identify assertion-only pruning explicitly. For a removed test in the selected diff, assess whether its unique protection survives.

### Verification

Give the baseline command and result. If experiments ran, include this table:

| Evidence                        | Deliberate change                  | Expected result                          | Observed result                                |
| ------------------------------- | ---------------------------------- | ---------------------------------------- | ---------------------------------------------- |
| Evidence identifier used above. | Specific fault or internal change. | Which test should detect or tolerate it. | Actual test result and relevant failure point. |

Provide the command or reproducible experiment description for each result. Keep expected and observed outcomes separate. Omit the experiment table when none ran and state why.

### Limits

State what remains unverified and why. Distinguish narrower test coverage from a defect in the behavior it claims to protect. Name any unresolved contract decision and the evidence needed to settle it. If there are no material limits, say so briefly.

If the selected scope contains no reviewable tests, replace the tables with the scope, the inspection result, and any blocker. Do not emit empty templates.
