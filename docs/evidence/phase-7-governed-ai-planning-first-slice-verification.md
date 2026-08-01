# Phase 7 Governed AI Planning First-Slice Verification

## Candidate identity and authority

- Repository: `/Users/danke/Developer/VisualEngineer`
- Baseline branch/revision: `main` at
  `9c282e91a42a87ea553171d5aa55a0f77564bb14`
- Candidate branch: `codex/phase-7-governed-ai-planning-first-slice`
- Baseline state: tracked diff, index, and untracked set clean; no remote; no
  stash; sole migration head `20260801_0014`.
- Candidate migration head: `20260801_0015`.
- Authority: deterministic fake Provider and fixture-only planning. No API key,
  Provider SDK/network call, CreativeDeploy, Customer 0, real repository,
  remote Git, push, PR, merge, tag, or deployment was used.

## Implemented evidence boundary

The candidate persists one exact revision/Snapshot-bound `AIPlanRequest`,
versioned Prompt and digest, redacted bounded context manifest, strict typed
request/response and deterministic digest, Provider capability metadata,
attempt Trace with synthetic non-billable usage/cost, eleven system-owned Eval
results, and one append-only human decision. Approval creates only one existing
`Plan` handoff with `source = governed_ai` and `execution_available = false`.
Database assertions confirm it creates zero Execution Grants, Review
Decisions, and Delivery Authorizations.

## Focused verification

| Boundary                  | Command/result                                                                                                                               |   Exit |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | -----: |
| AI API/PostgreSQL/Eval    | `pytest test_governed_ai_evals.py test_governed_ai_planning.py --no-cov -q`: `13 passed`                                                     |      0 |
| Python typing             | `uv run mypy`: 131 source files                                                                                                              |      0 |
| Web unit/component        | `pnpm test`: 10 files, `60 passed`                                                                                                           |      0 |
| Web typing/lint/build     | `pnpm typecheck`; `pnpm lint`; `pnpm build`                                                                                                  | 0 each |
| Eval manifest             | `uv run python scripts/validate_evals.py`: 85 deterministic cases across 7 datasets                                                          |      0 |
| API contract generation   | `make contracts`; generated OpenAPI and TypeScript schema updated                                                                            |      0 |
| Real browser focused flow | `./scripts/run-e2e.sh phase7-governed-ai-planning.spec.ts`: desktop/narrow approve/reject, `4 passed`, axe/no-overflow and source invariance |      0 |

The PostgreSQL matrix includes exact replay/idempotency, redaction, context
budget/reference closure, all eleven Eval rows, stale revision approval denial,
reasoned rejection, cancellation, bounded retry, timeout/cancel/failed error
classification, concurrent approve/reject one-winner behavior, AI evidence
immutability, and zero downstream authority issuance.

## Preserved first failures

1. The first focused backend run failed five cases because PostgreSQL JSONB
   stored Python `None` as JSON `null`, an optional path validator rejected
   `None`, and the evaluator attempted to serialize a nested Pydantic value.
   The production mapping/validation/serialization paths were corrected; the
   unchanged focused boundary then passed and was extended to 13 cases.
2. The first browser run failed all four project cases with exit `1` because
   the test locator for `Acceptance criteria` matched both a heading and an
   Eval sentence. The locator was narrowed to its semantic heading.
3. The next browser run completed both business flows but failed all four axe
   checks with exit `1`: the bounded scrollable context list was not keyboard
   focusable. The list received an accessible name, keyboard focus, and a
   visible focus ring. A rebuilt-image rerun passed `4/4` with exit `0`.
4. The only complete `make verify` run reached Python `330/330` and Web
   `60/60`, then failed with exit `2` because Web function coverage was
   `69.89%`, below the `70%` threshold. An interaction regression exercised
   freshness, reasoned rejection, cancellation, and approval; focused Web
   coverage then passed with `71.42%` functions. The complete aggregate was
   not rerun.
5. The resumed tail first stopped at `security-check` with exit `2` because
   two synthetic secret-shaped fixture literals were visible to the static
   secret scanner. Both fixtures now assemble the same adversarial values at
   runtime; `check-secrets.sh`, the complete security target, and Eval tail
   all pass. No real secret was present or requested.

These failures are evidence of corrected implementation/test defects, not
independent review findings or a Security Gate decision.

## Source and Docker invariance

The focused and full real-browser scripts hash fixture `HEAD` and porcelain
status before and after, and exit successfully only when both fixture
repositories remain invariant and no lifecycle marker executes. Task-owned
E2E, Chaos, and test-database projects use exact cleanup traps. Pre-existing
`visualengineer` platform services and the unrelated CreativeDeploy PostgreSQL
service remain outside this slice and untouched.

## Aggregate and checkpoint

- Complete `make verify`: run exactly once; **exit `2` preserved**, solely at
  the then-current Web function coverage result (`69.89% < 70%`) after Python
  `330/330` and Web `60/60` passed. The coverage defect is corrected and the
  focused coverage command passes at `71.42%`; the aggregate was not rerun.
- The unexecuted aggregate tail was run target-by-target after remediation:
  build/Compose/Migration pass; Phase 4 audit `25/25`; repair matrices `95/95`
  and `14/14`; full Playwright desktop/narrow `20/20`; Workspace security
  `70/70`; Runner security `121/121`; Review security `20/20`; Eval `85`
  deterministic cases plus repository scanner `7/7`; Workspace chaos,
  validation sandbox, secret scan, source invariance, and Docker cleanup pass.
- Final diff review: pass. Local checkpoint is created after this document;
  its exact hash is reported in the post-commit handoff.
- Independent focused review, sealing, main integration, real Provider, and
  production readiness: **NOT VERIFIED / NOT AUTHORIZED**.
