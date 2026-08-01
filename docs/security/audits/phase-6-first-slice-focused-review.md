# Phase 6 First Vertical Slice Independent Focused Review

- Review date: 2026-08-01 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Candidate: `b80122a51debf26aa739a599f448a8b68c074527`
- Main baseline: `962b72ec92329de929ca5f9381b5324a68a18dde`
- Review branch: `audit/phase-6-first-slice-focused-review`
- Independence: no production implementation was changed
- Status: **COMPLETE — FAIL — REMEDIATION REQUIRED**
- Remote CI: **NOT VERIFIED**

## Verdict

`PHASE 6 FIRST SLICE FOCUSED REVIEW FAIL — REMEDIATION REQUIRED`

One blocking Medium Delivery security Finding is confirmed. The candidate does
not fail closed when managed-mirror state becomes unexpected after Workspace
prepare but before governed local commit. Per the review stop rule, the full
`make verify` aggregate was not run, no sealing commit was created, and main
was not moved.

## Finding VE-P6-FSR-001

- Severity: **blocking Medium**
- Trigger: after a valid prepare and governed write, introduce an unexpected
  loose ref, packed-ref state, or replacement metadata into the managed mirror,
  then execute an otherwise valid governed local delivery.
- Expected: typed `workspace_state_invalid`, no target delivery ref, and no
  source-repository mutation.
- Actual: all three cases return `WorkspaceGitCommitResult` and create the
  target delivery ref. The source repository remains unchanged.
- Stable reproduction: three consecutive confirmation runs, each `3 failed`
  in approximately 1.1 seconds; the formal security target reports
  `22 passed, 3 failed`, Make exit `2`.
- Evidence:
  `apps/runner/tests/security_audit/test_phase6_first_slice_focused_review.py`
- Production/gate tree status: unchanged from the candidate; frozen tree
  SHA-256 `c1448fc7b7929f7fbc015e40ea94c8c9eae5c46fcb187421f93d45b2b5b6b7e3`.

The prepare path validates an existing managed mirror, but the delivery path
reaches fixed Git plumbing and ref mutation without repeating the common
managed-mirror validation. The target ref remains correctly derived and the
source remains read-only, but those narrower controls do not satisfy the
required fail-closed boundary for unexpected persisted Git state.

## Narrow remediation boundary

Keep remediation inside the Runner managed-mirror delivery boundary:

1. serialize prepare/delivery operations for the same managed mirror;
2. immediately before any delivery object or ref mutation, revalidate the
   common Git directory, config, object format, allowed ref namespace,
   packed/replacement state, source lineage, and existing delivery-object
   budgets; and
3. return typed `workspace_state_invalid` with zero target-ref mutation when
   validation fails.

Retain `VE-P6-FSR-001` unchanged as the permanent regression test. No API,
Web, migration, authorization TTL, lease, attempt, timeout, or retry expansion
is needed for this Finding.

## Other focused results

The candidate's existing focused tests pass for the four distinct
authorization layers, create/decision/dispatch state machine, Permit and
binding denial paths, fixed Git plumbing, derived delivery ref, deterministic
single-parent commit, multiple delivery-root object closure, object budgets,
source invariance, migration 0013, and the `/deliveries` browser flow.

The complete Playwright run passes `16/16`; its Phase 5 validation scenario
contains the Phase 6 `/deliveries` create, approve, dispatch, polling, success
proof, and no-remote/source-invariance assertions on desktop and narrow
Chromium.

## Workspace Chaos attribution

The candidate and main use byte-identical Chaos harness scripts. Under the
same isolated Compose name, ports, default lease/TTL/attempt/timeout values,
and full-build policy:

| Revision  |  Run 1 |  Run 2 |  Run 3 | Target failure signatures |
| --------- | -----: | -----: | -----: | ------------------------- |
| candidate | 67.68s | 66.42s | 66.77s | none                      |
| main      | 77.41s | 66.90s | 65.95s | none                      |

All six runs pass with two prepare attempts, four write attempts, three stale
leases fenced, zero budget replay, zero discard residue, zero post-revocation
side effects, unchanged fixture HEAD/status/tree fingerprints, and zero
Compose residue. This review therefore confirms no new deterministic Chaos
regression and does not reproduce `envelope_expired`, `retry_exhausted`, or a
recovered prepare failure in either revision.

## Gate disposition

- Focused Runner/Protocol, API, and Web unit selections: PASS.
- Contracts, format, lint, typecheck, build, and Compose render: PASS.
- Existing candidate Security, Workspace Security, Validation Security, Phase
  4 findings/repair, and source invariance: PASS on the exact candidate tree.
- Migration 0013 base/head/base/head and sole head: PASS.
- Playwright E2E: PASS, `16/16`.
- Independent security extension: FAIL, `VE-P6-FSR-001`.
- Candidate/main Workspace Chaos comparison: PASS, `3/3` each.
- Full `make verify`: **NOT RUN by stop rule**.
- Sealing, main movement, fetch, push, PR, tag, and deploy: **NOT PERFORMED**.
