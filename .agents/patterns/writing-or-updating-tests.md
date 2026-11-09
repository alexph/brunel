# Writing or updating tests

## Place tests in the repository test suite

Put tests in the repository's `tests/` folder. Move existing tests only when that migration is part of the requested work.

## Split files by the behavior they cover

Use focused files within `tests/`. Group related behavior rather than creating one file per test or collecting unrelated tests in one large file.

When a group becomes difficult to navigate, split it by a coherent feature or behavior. Do not mirror every private production module mechanically.

## Keep endpoint authorization checks beside the endpoint tests

Given an authorization check for an API endpoint, add a focused test beside that endpoint's existing API tests. Authorization is part of the endpoint's behavior.

Prefer extending the existing API test file over creating a separate authorization or policy suite. Name the test for the operation and denial, such as `test_create_tag_bearer_denied_403`. Assert the status required by the endpoint's contract. Some endpoints deliberately return 404 for denied access, so do not impose 403 universally.

Set up the relevant denied credential or permission, call the endpoint, and assert the denial. For a mutation, also check that the relevant state or external effect remains unchanged when that is part of the claim. Reuse the existing API client and fixtures where suitable.

Do not collect unrelated endpoints into an authorization matrix or build a separate test harness merely because they share an auth mechanism. Group tests of shared authentication and policy mechanics by the component that owns those mechanics. Endpoint tests need to establish that each endpoint applies the appropriate restriction, without repeating the shared mechanism's full test matrix.

## Reuse fixtures before adding setup

Read the applicable `conftest.py` files and nearby tests before creating a fixture.

Reuse fixtures that already provide the required setup. Do not recreate those fixtures locally under different names.

Given a scenario that needs different state, build on a suitable fixture or add focused setup for that scenario. Keep newly shared fixtures in the narrowest `conftest.py` that covers their consumers. Do not move every fixture to the root.

## Test the behavior owned by the layer

Test the observable behavior of the interface under test. Trust internal interfaces with established direct coverage. Do not repeat their full test cases in every caller's tests or assert how their private implementation works.

For example, given a component with database tests for its persistence rules, a caller's tests should cover the caller's decisions and results. They do not need to repeat every field-persistence assertion from the component's tests. Retain integration coverage when the connection between the caller and component introduces a distinct risk.

## Use real behavior by default

Use real internal collaborators and database behavior when they establish the result under test. In particular, test database-backed operations against the database.

Reserve mocks for expensive operations, especially external API and AI calls. A higher-level test may also mock an internal interface whose database behavior already has direct test coverage, when repeating that work adds cost without useful coverage.

Before mocking such an internal interface, inspect its direct tests. Do not assume the database behavior is covered. Keep a real integration test where the connection between layers is itself the behavior at risk.

Assert observable results, errors, persisted state, and required external effects. Avoid asserting internal helper calls or call order unless those interactions are part of the contract. A mocked dependency's return value alone does not prove the real dependency works.

## Give each test one behavioral claim

Each test must have one aim that its name can state precisely. Keep setup, the operation under test, and assertions readable from top to bottom. A reviewer should be able to assess that claim without untangling unrelated operations or changes to credentials midway through the test.

Split create, list, detail, update, and delete guarantees into separate tests. Keep successful access, scope denial, and foreign-resource denial separate too. Do not combine them into a CRUD journey merely because they use the same record or client.

One aim can require several assertions. A denied mutation test should establish both the denial response and the absence of the forbidden change. A retry invariant may require two calls to establish that no duplicate is created. Do not impose one assertion or one call per test.

When cleaning up existing tests, moving a long scenario into the correct file does not finish the readability work. Split its independent claims and preserve their coverage. Relocation alone is sufficient only when the task explicitly limits the work to moving files.

Keep setup and assertions short enough that the scenario and expected result are apparent. Supply the inputs needed for that scenario and let fixtures provide unrelated baseline state.

An invariant is a property that must remain true across the relevant cases. Test an invariant directly. Do not repeat every input parameter or output field in every test when those details do not affect the claim.

Given a test for duplicate invite handling, assert that duplicate emails produce one invite. Do not also repeat assertions for every default field on an invite. Cover field persistence separately when that behavior needs protection.

Use parameterization when distinct inputs exercise the same rule. Include cases that could expose different failures. Do not add combinations of unrelated parameters merely to increase the case count.

Short tests must still establish the promised behavior. Preserve unique regression cases, and use exact expected values when the contract requires them.

## Use named HTTP status codes

Use `HTTPStatus` from Python's `http` module for HTTP status expectations, including parameterized cases.

## Prefer readable repetition over test helpers

Tests do not need to be DRY. Prefer a linear sequence of setup, action, and assertions that a reader can follow from top to bottom. Avoid creating test helpers. They add names and indirection, forcing the reader to jump between definitions to reconstruct the scenario. Accept repetition when it preserves that linear readability. Two similar blocks or a particular line count do not by themselves justify extraction.

Consider a helper only when substantial incidental mechanics obscure the test more than the indirection would. A repeated signing protocol or substantial resource cleanup may qualify. Keep the scenario's inputs, action, and expected outcome visible in the test. Do not wrap a straightforward request or a few assertions merely to shorten the test.

Avoid helpers with flags or branches for different test scenarios. Keep those differences explicit in the tests. Do not extract assertions merely to make tests look shorter or conceal a repeated field checklist.

Continue to reuse established fixtures for baseline resources. This rule permits repetition of scenario-specific steps; it does not justify duplicating shared fixture definitions.

## Assert what distinguishes each branch

Given several tests for branches of the same operation, cover shared field mapping or persistence in a representative test. In the other branch tests, assert the outcome that distinguishes that branch. Do not repeat a full field checklist or hide it in a shared assertion helper called by every test.

For example, an invite operation may create an invite, reuse an existing invite, or reject a denied request. The creation test can cover field persistence. The reuse test should establish that the existing invite is returned without creating a duplicate. The denial test should establish rejection and the absence of the forbidden change.

Repeat a field assertion when the branch could independently map, change, omit, or corrupt that field. A representative test covers only the shared behavior it actually exercises. Do not remove branch-specific regression coverage merely because another branch asserts the same field.

## Test consequential migration behavior

Test custom data migrations when incorrect transformation could corrupt or lose data, or when compatibility with existing records needs verification. Keep migration tests focused on those risks. Exercise the migration against the historical schema and records it uses. Tests of current application behavior do not establish that the migration works.
