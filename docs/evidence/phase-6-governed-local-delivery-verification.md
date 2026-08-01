# Phase 6 governed local delivery verification

- Date: 2026-07-31 +08:00
- Repository: `/Users/danke/Developer/VisualEngineer`
- Main baseline: `962b72ec92329de929ca5f9381b5324a68a18dde`
- Branch: `feat/phase-6-governed-local-delivery`
- Candidate status:
  `PHASE_6_LOCAL_DELIVERY_IMPLEMENTED_FOCUSED_VERIFIED_AGGREGATE_GATE_OPEN`
- Security decision: not made by this implementer

## Preflight and Phase 6 definition

The preflight confirmed the exact Developer repository root, clean local
`main`, HEAD/main/merge-base at the declared baseline, no tracked/cached or
untracked diff, no remote, no stash, the complete local refs, Git identity,
and the sole Alembic head `20260730_0012`. The similarly named
`/Users/danke/Documents/VisualEngineer` directory is a different empty Git
repository and was not used.

The repository did not name a standalone Phase 6 milestone. Its product and
architecture roadmap reserved three V1 seams: LLM/agent execution,
non-fixture target commands, and Git delivery. The user stop boundaries
excluded the first two, real repositories, credentials, and every remote
operation. A concise Inception therefore selected the only unambiguous safe
direction: one separately approved, fixture-only local branch and commit
inside Runner-owned state.

No Phase 0–5 implementation or independent decision was reopened. No
CreativeDeploy, Customer 0, real customer repository, LLM, Agents SDK, model
Provider, API key, authentication, multi-tenancy, remote, push, pull request,
merge, tag, deploy, source-repository write, irreversible migration, or data
deletion was introduced or exercised.

## Implemented vertical slice

Migration `20260731_0013` adds immutable delivery authorization, decision, and
local-result tables plus additive Runner/Workspace bindings. Foreign keys,
closed enums, one-winner constraints, zero-remote checks, audit guards, and
update/delete triggers fence the exact Review generation, approving decision,
effective ready verdict, original implementation Grant, Workspace,
Checkpoint, source revision, and result.

The API exposes separate create, decide, and dispatch operations. It derives
`refs/heads/visual-engineer/<workspace-id-hex>`, the commit message, identity,
timestamp, and 15-minute authority window. It rejects empty reviewed diffs,
stale readiness, caller-injected authority, replay, cancellation, and all
remote capability before dispatch.

Protocol version `0.6.0` adds one closed
`workspace_git_commit_v1` capability. The Job carries both the original
Workspace Execution Grant and the exact Delivery Authorization. A short-lived
Side-effect Permit binds Runner, Job, Attempt, Lease, both authorities,
Workspace, Checkpoint/diff, operation digest, and deadline.

The Runner constructs a tree with a temporary alternate index and fixed Git
plumbing, then creates one deterministic commit and performs one old-OID
guarded local ref update. Hooks, signing, credentials, filters, helpers,
network, remote operations, source refs, source bytes, Workspace HEAD, and
Workspace bytes remain absent or unchanged. Temporary indexes are removed.

Mirror reuse admits only a bounded loose
`refs/heads/visual-engineer/<workspace-id>` namespace. Every ref is read
no-follow with stable metadata, targets one commit whose sole parent is the
approved source revision, and participates in an exact union of the source
object closure and all retained governed delivery closures. Packed,
replacement, arbitrary, malformed, tampered, over-budget, or unreachable
state fails closed.

The `/deliveries` Web flow shows candidate selection, separate approval or
reasoned rejection, dispatch, terminal polling, durable local proof, and
explicit zero-remote wording. Long refs and object IDs wrap at narrow width.

## Verification ledger

| Boundary                            | Result                                                                                                                                                                                                                   |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| focused Phase 6 Protocol/API/Runner | final exact-source Phase 6 API plus complete Runner/Protocol 71/71; earlier narrow 12/12 covered actual commit, missing-Permit, replay, zero source mutation, stale/injection/cancellation denial                        |
| governed ref reuse/security         | 5/5 plus post-review 2/2; one- and two-delivery-ref sibling prepare, arbitrary/replacement ref denial, parent-lineage tamper denial, local-ref budget, exact source invariance                                           |
| focused Web                         | 3/3; separate decision, no remote control, dispatch plus terminal polling                                                                                                                                                |
| full Python/API/Runner/Protocol     | 300/300; 83.33% aggregate coverage before the final no-semantic dead-branch cleanup; final exact-source focused set 71/71                                                                                                |
| Web                                 | 53/53 across 10 files; statements 71.41%, branches 68.62%, functions 70.47%, lines 72.86%                                                                                                                                |
| contracts and static checks         | generated OpenAPI/TypeScript no drift; Ruff/Prettier/ESLint pass; mypy 115 source files; TypeScript pass                                                                                                                 |
| production build and Docker config  | pass; Next.js emits `/deliveries`; all Compose variants validate                                                                                                                                                         |
| real PostgreSQL migration           | base → `20260731_0013` → base → `20260731_0013`; one sole head                                                                                                                                                           |
| complete browser real stack         | desktop and narrow 16/16; local commit, persistence, axe, containment, revocation, discard, fixture invariance                                                                                                           |
| Phase 4 historical preservation     | six controls present; historical independent FAIL preserved; audit 22/22                                                                                                                                                 |
| Workspace repair/source invariance  | 89/89 plus API 14/14; 119 source entries, 10 Git objects, 2 status records, zero extension markers                                                                                                                       |
| Workspace Chaos                     | one exact isolated PASS with atomic pre/post-rename recovery, four writes, three stale leases fenced, zero post-revoke effects/residuals, source and `.git` unchanged; four final-source attempts failed during recovery |
| Workspace/Validation security       | Workspace/Protocol 67/67; descriptor/static checks; Landlock filesystem denial; seccomp network denial; fixed Profiles pass/fail                                                                                         |
| broad security                      | secrets/static Runner boundaries pass; scanner 7/7; Runner/API/Protocol 114/114; Review 20/20                                                                                                                            |
| deterministic Eval                  | 74 cases across six datasets plus scanner 7/7                                                                                                                                                                            |
| aggregate                           | pre-review source exited 0 but was superseded by the two-ref Diff finding; post-review attempts reached Workspace Chaos after preceding gates passed, then exited 2; final aggregate Gate open                           |
| whitespace                          | independent final `git diff --check`, exit 0                                                                                                                                                                             |

The formal E2E script compared synthetic source and canonical Workspace HEAD,
status, and tree fingerprints before and after. The Chaos harness independently
verified its source repository and `.git` fingerprint. Their exact task-owned
containers, volumes, and networks were removed by cleanup traps.

Post-verification Docker inspection found no task-owned
`visualengineer-e2e`, `visualengineer-test-db`, or
`visualengineer-workspace-chaos` containers, volumes, or networks. The
pre-existing `visualengineer-db-1`, `visualengineer-api-1`,
`visualengineer-web-1`, and `visualengineer-runner-1` development containers
remained running and were not touched.

## First failures and exact recovery

Failures are retained as evidence and are not counted as passing runs:

1. The first combined Protocol run exposed the old maximum-operation bound
   and a backward-compatibility change in Permit hashing. The bound now
   includes the closed Git operation and an absent delivery authority remains
   omitted from the legacy digest; focused tests passed.
2. The first API run found no PostgreSQL service, then found that the shared
   test cleanup omitted the three new tables. The exact test database was
   started and explicit no-`CASCADE` cleanup lists were extended.
3. The first real create received `409` because the historical audit-event DB
   allowlist rejected the new events. Migration upgrade/downgrade now extends
   and restores that guard exactly.
4. The first missing-ref probe treated Git return code `128` as absence. It
   now uses `rev-parse --verify --quiet`, whose expected absent result is `1`.
5. One combined pytest ordering put populated Phase 6 rows before an older
   full-history migration downgrade test. Clean base/head roundtrip passed in
   isolation and in the final aggregate.
6. Initial browser delivery had an empty diff, then incorrectly reused the
   Phase 5 validation Grant with a one-byte diff budget. The E2E now creates a
   real reviewed fixture change; delivery reuses the original implementation
   Grant and adds only the separate local-commit authority.
7. A successful Runner Job remained visually `dispatched` because the Web
   console did not poll terminal state. Bounded 500 ms polling and a component
   regression were added; all Web tests passed.
8. The first full aggregate stopped on generated OpenAPI drift. Contracts were
   regenerated and `contracts-check` passed. The next aggregate reached
   298/299 before `test_task_concurrency` exposed its private TRUNCATE-list
   omission; the exact list was fixed and the focused PostgreSQL test passed.
9. The following aggregate stopped immediately on Ruff formatting of that
   fixture edit. The repository formatter made the no-semantic-change repair.
10. The first complete post-delivery browser matrix exposed the Phase 4 empty
    mirror-ref invariant: the valid local delivery ref caused every later
    Workspace prepare to fail `workspace_state_invalid`. Allowing only the
    bounded fixed namespace was insufficient because the exact destination
    object closure also rejected delivery objects. The final invariant
    validates both the fixed refs and exact source-plus-delivery closure; post-
    delivery prepare and ref tamper/budget tests pass.
11. Loaded full-matrix attempts also exposed asynchronous Suite Evidence
    rendering beyond a default 5-second assertion and two host/Docker pause-
    shaped intervals where Jobs stayed `queued` without typed error. The
    Evidence assertions were aligned with the Suite terminal window. The exact
    two-test sequence passed 2/2, the isolated narrow delivery passed 1/1, and
    two later complete matrices passed 16/16 without changing authority,
    product timeout, or expected state.
12. The first otherwise complete narrow flow found horizontal overflow from
    the unbroken branch ref. The flex item now permits shrinking and the ref
    wraps; the narrow real-stack rerun and final 16/16 matrix passed.
13. Final Diff review found that mirror reuse replaced, rather than accumulated,
    the retained object closure for each governed local ref. A two-ref regression
    reproduced the missing union. The closure now accumulates every validated
    delivery root; the exact two-test ref suite passes 2/2.
14. The first post-review aggregate and its immediate isolated Workspace Chaos
    rerun both stopped at the recovered write with `envelope_expired`. No TTL,
    authority, or timeout was changed. A third identical isolated run passed
    with two prepare attempts, four write attempts, three stale leases fenced,
    zero post-revocation effects or residuals, and unchanged source and `.git`
    fingerprints.
15. The next aggregate stopped at `format-check` because the two new Evidence
    entries had not yet been passed through Prettier. The repository formatter
    made the documentation-only repair before the final aggregate rerun.
16. The next post-review aggregate reached Workspace Chaos after every
    preceding gate and browser 16/16 passed, then stopped at recovered write
    with `retry_exhausted`. A final exact-image isolated run failed earlier
    while waiting for recovered prepare. Repeated retries were stopped; no
    lease, attempts, TTL, timeout, or authority was widened. The aggregate Gate
    remains explicitly open.

## Final boundary

This is implementation and current verification evidence only. It does not
declare an independent focused-security-review PASS, Security Gate PASS,
sealing, local `main` integration, remote delivery, production readiness, or
authorization for any remaining Phase 6 direction.

The local checkpoint is created only after this evidence is frozen and the
final diff/scope review passes. Its hash and the final clean
worktree/index/untracked state are reported in the handoff; a commit cannot
contain its own hash.
