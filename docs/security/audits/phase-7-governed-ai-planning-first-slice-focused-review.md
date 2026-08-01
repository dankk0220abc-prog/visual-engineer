# Phase 7 Governed AI Planning First-Slice Independent Focused Review

- Review date: 2026-08-02 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Candidate: `78747441bb41c1c0a42fc38d8ba33f6cae12ad0a`
- Main baseline: `9c282e91a42a87ea553171d5aa55a0f77564bb14`
- Review branch: `codex/audit-governed-ai-planning-first-slice-final`
- Independence: no production code, migration, generated contract, or existing
  test was changed
- Status: **COMPLETE - FAIL - REMEDIATION REQUIRED**
- Remote CI: **NOT VERIFIED**

## Verdict

`GOVERNED AI PLANNING FIRST SLICE FOCUSED REVIEW FAIL — REMEDIATION REQUIRED`

One blocking Medium Finding is confirmed. A consistently deterministic and
replayable fixture Provider response can carry a Prompt binding different from
the immutable request and can relabel a grounded package-manager fact as a
framework fact while all eleven system-owned Eval results still pass. This
violates the exact Prompt binding and hallucinated-repository-fact rejection
requirements.

Per the review stop rule, the full `make verify` aggregate was not run, no
sealing commit was created, and `main` was not moved.

## Finding VE-P7-AIP-FR-001

- Severity: **blocking Medium**
- Trigger: return the same valid typed response on every replay, but change
  the response Prompt version/digest and change a repository finding's semantic
  kind while retaining a real context reference and its exact summary.
- Expected: a binding or grounding Eval fails; the response cannot satisfy the
  mandatory approval gate.
- Actual: all eleven Eval IDs report `passed=true` while
  `plan.prompt != request.prompt` and the finding kind does not match the kind
  of its referenced context entry.
- Finding: the grounding check compares finding summary text with referenced
  summary text but does not verify their semantic kind; the Eval path also does
  not compare the response Prompt binding with the immutable request binding.
- Production tree status: unchanged from candidate tree
  `8f6d9ee31074b04df742548d8935d4148700873e`.

The installed deterministic fake currently emits the expected bindings and
kind mapping. That happy path does not close the independent system-owned Eval
boundary: the Provider response is the untrusted object the Eval layer is
required to verify, and exact deterministic replay only proves consistency,
not truth or correct binding.

## Narrow remediation boundary

Keep remediation inside the AI Plan contract/Eval boundary:

1. compare the response Prompt template ID, version, and digest with the
   immutable generation request;
2. validate every repository finding's semantic kind against each supporting
   context entry, in addition to its reference and summary;
3. add unchanged negative regressions using a consistently deterministic
   fixture Provider so replay cannot mask either mismatch; and
4. prove a mismatched response remains failed and cannot receive a human
   decision or create a handoff Plan.

No real Provider, SDK, credential, network, Runner, Git, TTL, retry, migration,
or wider authorization change is needed.

## Other focused results

- Provider interface and installed runtime are model-vendor neutral and contain
  no real SDK, network call, API key, or credential dependency.
- Default fake generation/replay, bounded retry, timeout/cancel classification,
  PostgreSQL idempotency, freshness, one-winner approval, append-only evidence,
  redaction, prompt-injection fixture, and zero automatic downstream authority
  pass the candidate tests.
- AI PostgreSQL/Eval tests pass `13/13`; Web tests pass `60/60` with function
  coverage `71.42%`; focused desktop/narrow Playwright passes `4/4`.
- Contracts, format, lint, Python/TypeScript typecheck, Web build, Migration
  `20260801_0015`, deterministic Eval manifest, secret scan, source invariance,
  and `git diff --check` pass.

These narrower PASS results do not override `VE-P7-AIP-FR-001`.

## Gate disposition

- Focused review: **FAIL**.
- Full `make verify`: **NOT RUN by stop rule**.
- Fresh aggregate coverage: **NOT RUN**; focused Web coverage is `71.42%`.
- Sealing: **NOT PERFORMED**.
- Main movement, remote access, push, PR, tag, deploy, and real Provider use:
  **NOT PERFORMED**.
