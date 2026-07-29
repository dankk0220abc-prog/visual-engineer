# ExecPlan Standard

An ExecPlan is a living implementation record for work that spans multiple
components, has meaningful risk, or cannot be completed and verified in one
small edit. It must let a new engineer resume safely without relying on chat
history.

## Required sections

Every plan under `docs/exec-plans/` contains:

1. **Goal**: the observable user or system outcome.
2. **Scope**: files, services, and behaviors that may change.
3. **Non-goals**: attractive but excluded work.
4. **Constraints and safety**: permissions, sensitive data, destructive
   operations, and stop conditions.
5. **Current progress**: dated, checkable steps marked `pending`, `in progress`,
   `done`, or `blocked`.
6. **Decisions**: chosen approach, rationale, and alternatives rejected.
7. **Risks**: likelihood, impact, mitigation, and owner or next action.
8. **Discoveries**: facts learned during implementation, clearly separated from
   assumptions.
9. **Verification**: exact commands, environments, exit codes, and concise
   results. Unrun checks say `NOT YET VERIFIED`.
10. **Rollback**: how to stop services and reverse the scoped change without
    damaging unrelated work.
11. **Completion conditions**: objective gates that must all hold.
12. **Outcome and follow-ups**: actual result, deviations, residual risks, and
    the next coherent milestone.

## Maintenance rules

- Create the plan before risky or cross-cutting implementation begins.
- Update progress and discoveries as they happen, not as a retrospective.
- Record a failed verification before or alongside the fix; do not erase useful
  failure history.
- Include timestamps with a timezone when sequence matters.
- Prefer evidence links over copied logs. Never include credentials or
  unnecessary personal paths.
- A checked box means the work and its required verification are complete.
- A plan is not complete while a mandatory gate is failing or unverified.
- Scope changes require a decision entry and matching updates to product,
  architecture, security, and status documents where applicable.
- Close with the checkpoint hash only after a commit exists and the final
  worktree state has been inspected.

## Status vocabulary

- `IMPLEMENTED`: present in the inspected worktree; not necessarily exercised.
- `VERIFIED`: supported by a current command or manual check with evidence.
- `NOT YET VERIFIED`: present or planned but not exercised successfully.
- `PLANNED`: described but not implemented.
- `BLOCKED`: cannot proceed inside the current safety or environment boundary.

The active plan is
[`docs/exec-plans/phase-5-governed-validation-suites.md`](docs/exec-plans/phase-5-governed-validation-suites.md).
This second Phase 5 slice composes the sealed fixed-Profile execution unit into
one system-owned, immutable, fixture-only multi-step Suite with deterministic
serial dispatch, aggregate budgets/evidence, cancellation, and one bounded
retry. It does not weaken the first-slice command, sandbox, Grant, Permit,
Attempt, Lease, cleanup, or invariance boundaries. It excludes LLMs, Agents
SDK, external providers, credentials, Customer 0, arbitrary commands, package
installation, Git delivery, and deployment.

The sealed first-slice plan remains at
[`docs/exec-plans/phase-5-governed-validation-execution.md`](docs/exec-plans/phase-5-governed-validation-execution.md);
its historical review, remediation, and re-audit records are unchanged.

The completed Phase 4 Final Integration Gate plan remains at
[`docs/exec-plans/phase-4-final-integration-gate.md`](docs/exec-plans/phase-4-final-integration-gate.md).
Its candidate was integrated into `main` by the explicitly authorized local
fast-forward sealed at
`928a89d2055d172bbd7c6670b42f668d103dcb03`. Historical audit FAIL decisions
and their later remediation and independent closure records remain unchanged.

The implementation plan remains at
[`docs/exec-plans/phase-4-isolated-workspace-tools.md`](docs/exec-plans/phase-4-isolated-workspace-tools.md),
and the independent audit plan remains at
[`docs/exec-plans/phase-4-max-security-audit.md`](docs/exec-plans/phase-4-max-security-audit.md).
The first repair and independent re-audit plans remain at
[`docs/exec-plans/phase-4-security-repair.md`](docs/exec-plans/phase-4-security-repair.md)
and
[`docs/exec-plans/phase-4-security-reaudit-max.md`](docs/exec-plans/phase-4-security-reaudit-max.md).
The Round 2 repair and focused re-audit plans remain at
[`docs/exec-plans/phase-4-security-remediation-2.md`](docs/exec-plans/phase-4-security-remediation-2.md)
and
[`docs/exec-plans/phase-4-security-focused-reaudit-max.md`](docs/exec-plans/phase-4-security-focused-reaudit-max.md).
The Round 3, single-finding re-audit, Round 4, and independent budget re-audit
plans also remain in `docs/exec-plans/`. None is rewritten as if the findings
never occurred.
The completed Phase 3 record remains at
[`docs/exec-plans/phase-3-browser-orchestrated-local-runner.md`](docs/exec-plans/phase-3-browser-orchestrated-local-runner.md).
The completed Phase 2 record remains at
[`docs/exec-plans/phase-2-readonly-repository-intelligence.md`](docs/exec-plans/phase-2-readonly-repository-intelligence.md).
The completed Foundation record remains at
[`docs/exec-plans/phase-0-1-foundation.md`](docs/exec-plans/phase-0-1-foundation.md).
