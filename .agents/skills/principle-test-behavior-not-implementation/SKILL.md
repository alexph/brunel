---
name: principle-test-behaviour-not-implementation
description: "Apply when you write, change, keep a tests. Assert what the code's users can observe, so that the test fails when that behavior breaks and keeps passing when only the internals change."
disable-model-invocation: true
---

# Test Behavior, Not Implementation

A useful test is a claim about what the code makes to its users. Behavior is what those users can observe through the interface they use. That includes values, errors, readable state, and effects on systems outside the code, such as a request sent, a row written, or a message emitted. Implementation is what they cannot observe: private helpers, internal call order, intermediate data, and which internal collaborator did the work.

Judge each test by two imagined edits:

- **Break the specific behavior this test claims to protect.** Make the code return a wrong value, skip a required effect, or perform it twice. If the test still passes, its assertions may not establish that claim. Before pruning, inspect companion tests and preserve unique regression cases and invariants. The usual causes are an assertion looser than the contract, an expected value computed by the code under test, a restated constant or prompt string that never runs the code that reads it, and an assertion on data that the test built itself.
- **Change the internals.** Keep every observable result the same and restructure the code underneath. If the test now fails, it is pinned to the implementation. It will need a rewrite on every refactor and still catches no bug.

Keep a test that catches the first edit and survives the second. Rewrite or delete the rest. To write a test that does both, drive the code through its users' interface with a concrete input. Derive the expected value from the requirement, not from a run of the code. Assert what the contract promises, no less and no more.

The contract decides, not the shape of the assertion. When "an empty cart never charges" is the promise, an assertion that the payment client got no call is behavior. Pair it with a case where the charge happens, so that the test shows it can see a call. The payload that a mocked external service receives is behavior, because that service observes it. A call to an internal helper is implementation, because no user can see it. An empty list is the exact answer when no record matches, and a hollow check when the test only needs some result. An exact error message pins wording that no caller reads. The error type that callers branch on is the contract.

A test can pin an invariant instead of a call, such as a key that must exist in two tables or a compile-time type check. The invariant is the behavior.

## Report pruned tests

Prune only within the task's scope. Inspect the removed and retained tests, and preserve unique regression cases. Run the relevant retained tests. When practical, confirm that a replacement catches the original fault.

Whenever tests are removed or replaced, include this table in the final response. Give each removed test its own row and identify individual parameter cases when applicable.

| Pruned test       | Behavior protected                     | Why pruned                                     | Retained or replacement test                                     | Verification                                          |
| ----------------- | -------------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------- |
| `path::test_name` | Concrete scenario and expected outcome | Specific redundancy or implementation coupling | `path::test_name`, or a specific reason no replacement is needed | Command and result, or explicitly not run with reason |

Name actual tests and explain how replacements preserve useful protection. Report verification limits plainly. Omit the table when no tests were pruned.
