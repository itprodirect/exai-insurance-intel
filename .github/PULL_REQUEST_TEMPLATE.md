## Summary

- What changed in this slice?

## Scope Boundary

- What was intentionally not changed?

## Validation

- What commands, tests, or manual checks were run?

## Risks / Follow-Ups

- What remains risky, unclear, or explicitly deferred?

## Single-Record Auth Check

Complete this only if the PR adds or changes a single-record route returning user-owned data.

- [ ] Explicit owner-or-ops enforcement exists at the route boundary
- [ ] Tests cover owner read
- [ ] Tests cover non-owner denial
- [ ] Tests cover ops read when allowed
