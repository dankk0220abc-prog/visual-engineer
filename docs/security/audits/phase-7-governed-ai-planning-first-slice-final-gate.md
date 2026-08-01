# Phase 7 Governed AI Planning First-Slice Independent Final Gate

## Decision

- Candidate: `8003c835284343be8c4046f868ec6d1f66369cef`
- Main: `9c282e91a42a87ea553171d5aa55a0f77564bb14`
- Review branch: `codex/audit-governed-ai-planning-final-20260802`
- Finding: `VE-P7-AIP-FR-001 PASS`
- Focused review: **PASS**
- Fresh full aggregate: **PASS**, exit `0`
- Auditor production/test changes: **none**
- Remote CI: **NOT VERIFIED**

## Verdict

`GOVERNED AI PLANNING FIRST SLICE FINAL GATE PASS — SEALED AND AWAITING EXPLICIT USER AUTHORIZATION FOR LOCAL FAST-FORWARD MAIN`

The candidate closes the sole Finding at the system-owned Eval boundary.
Consistently deterministic or replayable Provider output is not treated as
truth: exact Prompt/context/revision/Snapshot binding and exact repository-fact
identity/semantics/provenance are independently compared with immutable system
context.

## Finding disposition

### VE-P7-AIP-FR-001 — PASS

- Trigger: return the same valid typed response on every replay while changing
  the Prompt binding and relabeling an authoritative repository fact.
- Expected: binding and grounding Evals fail even though deterministic replay
  passes; approval and every downstream authority remain absent.
- Actual: `generation_binding_integrity=false`,
  `hallucinated_repository_fact=false`, and `deterministic_replay=true`.
  The failed Plan is durable and inspectable; approve returns
  `ai_plan_not_decidable`; same-key replay adds no Provider call or record.
- Production-hash status: unchanged from the exact candidate by the auditor.

The six generation-binding mutations and five fact-grounding mutations all
fail with reason-coded expected/actual evidence. Stale and grounding failure
coexist without masking each other.

## Eval and authority boundary

The exact twelve Eval IDs are current at `governed-ai-eval-v2`, unique,
blocking, trusted only as `system_policy`, and all required to PASS. Database
constraints preserve severity/trust and append-only evidence; approval also
checks exact ID set, version, severity, trust, and result.

Provider-authored Eval fields are outside the closed response schema and are
rejected before system evidence. A failed request creates no handoff Plan,
Execution Grant, Review Approval, Delivery Authorization, or Side-effect
Permit. A valid approval creates only the existing `governed_ai` Plan with
`execution_available=false`.

## Independent verification

- original Finding: `1/1`;
- complete AI Eval/PostgreSQL files: `34/34`;
- prompt-injection scanner: `1/1`;
- Web blocked-approval state: `1/1`;
- focused desktop+narrow browser: `2/2`;
- deterministic manifest: `94` cases across `7` datasets;
- source invariance: `119/10/2/0`;
- exactly one fresh `make verify`: exit `0`;
- Python: `351/351`, coverage `84.32%` against `80%`;
- Web: `61/61`, functions `71.49%` against `70%`;
- full Playwright: `20/20`;
- Workspace Chaos, Migration, Security, secret scan, and final diff: PASS;
- task project containers/networks/volumes: zero.

## External boundary

The runtime remains deterministic fake Provider and fixture-only. No Provider
SDK, network model, API key, secret, CreativeDeploy, Customer 0 data, real
customer repository, remote Git, push, PR, merge, tag, or deployment was used.
Docker BuildKit resolved pinned base-image registry metadata only for the
required local verification builds.

The historical FAIL report and Evidence remain permanent and unchanged.
`main` remains fixed. The only eligible next action after the local seal is a
separately and explicitly authorized local fast-forward of `main`.
