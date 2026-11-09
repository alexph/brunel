---
name: principle-boundary-discipline
description: 'Apply when parsing CLI arguments, config, requests, or external API responses; adding validation or error handling; or changing framework adapters. Establish trust at system boundaries, trust internal code, and keep domain logic pure.'
disable-model-invocation: true
---

# Boundary discipline

Place validation, type narrowing and error handling at system boundaries. Trust internal code unconditionally. Keep transport and framework details close to their adapters. Give
business rules an identifiable owner.

## Why

A boundary establishes a contract that internal code can rely on. Repeated defensive checks obscure that contract. Separating domain decisions from transport details makes the rules understandable without reconstructing framework wiring.

## Applications

### Validation and error handling

Parse raw inputs and reject unsupported values before internal logic relies on them. Inside that validated path, trust the established guarantees. Let broken internal contracts surface rather than hiding them behind fallbacks or swallowed errors.

Translate expected domain failures into responses at the adapter. Check again when data crosses another trust boundary or a guarantee can change. Authorization, concurrent updates, and historical persisted data may require checks at the point of use. Enforce mutable invariants atomically at their owner.

### Code organization

Adapters own request objects, wire formats, storage representations, and framework responses. Internal interfaces use domain concepts. The shell coordinates I/O and calls domain logic with explicit inputs. Domain logic owns business decisions and can be pure even when its caller performs I/O.

Separate code where doing so clarifies a responsibility. Extracting every expression into a helper or adding pass-through layers does not establish a useful boundary.

## Decision tests

- What untrusted input enters here, and what guarantee does this check establish?
- Has that guarantee already been established, and does it still hold? If so, the repeated validation is redundant.
- Can this rule change after input validation? If so, which owner can enforce it at the point of use?
- Is this an expected domain failure to translate, or a broken internal contract that must surface?
- Does this function make a domain decision or coordinate I/O? A pure function called by the shell can belong in the domain logic.
- Would this separation give a rule a clear owner, or merely add another layer?
