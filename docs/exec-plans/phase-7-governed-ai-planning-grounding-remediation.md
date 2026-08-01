# Phase 7 Governed AI Planning Grounding Remediation

- Started: 2026-08-02 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `codex/fix-governed-ai-planning-grounding`
- Repair baseline: `af71ecc5801a607849018b66e51b8e9986fd76da`
- Production candidate: `78747441bb41c1c0a42fc38d8ba33f6cae12ad0a`
- Main baseline: `9c282e91a42a87ea553171d5aa55a0f77564bb14`
- Finding: `VE-P7-AIP-FR-001`
- Status: **COMPLETE - READY FOR INDEPENDENT FOCUSED RE-REVIEW**

## Goal

Close only the system-owned Eval gap that allowed a deterministic Provider
response to change its generation binding or relabel a referenced repository
fact while remaining eligible for approval.

## Scope and boundaries

- Add exact Prompt registry/version/digest, context manifest digest,
  repository revision, and Snapshot response binding.
- Add exact fact reference, semantic kind, canonical value, source path, and
  canonical fact digest response binding.
- Compute blocking Eval results from the immutable system request/context.
- Keep failed proposals, Trace, and Eval evidence inspectable while preserving
  the existing failed-state approval gate, reject/cancel contracts, freshness,
  and one-winner decision behavior.
- Do not change Provider abstraction, migration, Execution Grant, Review,
  Delivery, real Provider/network/key, CreativeDeploy, or Git remote behavior.

## Design decisions

1. Add one `generation_binding_integrity` mandatory Eval and strengthen the
   existing `hallucinated_repository_fact` Eval instead of adding an approval
   state machine.
2. Extend the typed response binding because the old response had no field in
   which a context digest, repository binding, fact source, or fact digest
   could be represented and independently compared.
3. Require the approval gate to see the exact mandatory Eval ID set, current
   evaluator version, blocking severity, system-policy trust, and PASS result.
4. Keep Migration `20260801_0015` unchanged because existing JSONB response and
   Eval evidence columns store the stronger contract and additional Eval row.

## Progress

- done - governed Git preflight matched the exact audit checkpoint, candidate,
  main baseline, ancestry, clean index, and clean untracked inventory
- done - narrow repair branch created directly from the audit FAIL checkpoint
- done - Finding evidence, product, architecture, security, and active Phase 7
  implementation reviewed
- done - typed binding, evaluator, approval manifest, fixture Provider, focused
  API tests, Eval dataset, and explicit Web approval-blocked state implemented
- done - Finding-specific regression `1 passed`; final combined AI Eval,
  PostgreSQL, approval/replay/concurrency, and prompt-injection scanner set
  `41 passed`
- done - initial PostgreSQL test attempt preserved: exit `1`, test database
  port `55433` unavailable before any test body ran
- done - repository-owned test PostgreSQL started; final AI PostgreSQL file
  `17 passed`; exact test container then stopped and removed
- done - contracts/check, format/check, lint, typecheck, Web `61 passed`, and
  Next production build pass
- done - first focused browser attempt preserved: exit `1` on Docker Hub EOF
  before tests; isolated project cleanup confirmed
- done - focused browser retry with fresh images `4 passed` across desktop and
  narrow; source/Workspace invariance passed; exact project resources and image
  tags removed
- done - deterministic Eval manifest, secret scan, explicit source invariance,
  scope diff, and audit-document invariance pass
- prepared - focused repair checkpoint; commit ID reported after creation

## Outcome

`GOVERNED AI PLANNING GROUNDING REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-REVIEW`

This implementer does not declare the independent Finding or Phase 7 gate
PASS. No main movement, remote action, real Provider, or wider authority is
included.

## Rollback

Revert only the eventual repair commit. No schema rollback is required. Remove
only task-owned test/E2E Docker resources; do not stop or change pre-existing
platform services.
