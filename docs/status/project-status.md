# Project Status

- Phase: Phase 4 — Final Integration Gate
- Overall status:
  `PHASE 4 FINAL INTEGRATION GATE PASS — READY FOR USER-AUTHORIZED MAIN INTEGRATION`
- Governance qualifier: LOCAL FINAL GATE PASS; NOT IN MAIN; USER
  AUTHORIZATION REQUIRED
- Last updated: 2026-07-29
- Final integration branch: `integration/phase-4-final-gate`
- Final integration baseline:
  `38afe4b0c8eefa4c34b58e0b9d30cb74ca931501`
- Budget re-audit branch: `audit/phase-4-manifest-budget-reaudit-max`
- Independently audited Round 4 candidate:
  `03f774827afbafd7f0eb991f5abf2c6fee66cd17`
- Round 4 branch: `fix/phase-4-security-remediation-4`
- Round 4 base / single-finding audit:
  `2656733aad60d9824db4334b9ef6ba7eb1d677b8`
- Single-finding audit branch:
  `audit/phase-4-replacement-single-finding-max`
- Audited Round 3 candidate:
  `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`
- Round 3 branch: `fix/phase-4-security-remediation-3`
- Round 3 base / focused re-audit checkpoint:
  `8985fa0356e636602d1414a3ade9d9a7888c624a`
- Focused re-audit branch: `audit/phase-4-security-focused-reaudit-max`
- Focused candidate:
  `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`
- Round 2 branch: `fix/phase-4-security-remediation-2`
- Round 2 base / independent re-audit:
  `b457b614bde6630fb50ff9546c92a4d6925ad38a`
- Re-audit branch: `audit/phase-4-security-reaudit-max`
- Re-audited repair commit:
  `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c`
- Repair branch: `fix/phase-4-security-remediation`
- Repair base / audit commit:
  `a560509b2018f86693e38e3646409f9e33841829`
- Phase 4 implementation:
  `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main: `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Remote: none
- Remote CI: not run

## Final Integration Gate decision

The complete local Phase 4 Final Integration Gate is **PASS**.

**CONFIRMED**:

- the exact independently audited candidate and its ten-commit linear Phase 4
  ancestry were reconciled from unchanged `main`;
- all historical Critical, High, and blocking Medium Findings have later
  remediation plus independent closure evidence in the candidate ancestry;
- one final `make verify` exited `0`;
- Python passed `161/161` at 81.79% coverage and Web passed `41/41`;
- contracts, format, lint, typecheck, Next.js production build, all Compose
  rendering, real PostgreSQL migration roundtrip, 14 real Playwright cases,
  Workspace Chaos, security, and Eval passed;
- the named Runner and Workspace smoke targets both exited `0` against an
  isolated fresh Compose project; the Workspace rolled back and discarded,
  four policy-denial classes held, and source remained exact;
- the separate Runner offline/requeue Chaos target exited `0`;
- a live disposable runtime proved non-root Runner identity, read-only root
  and source, dropped capabilities, no-new-privileges, resource limits,
  internal API-only networking, blocked external TCP, narrow mounts, and
  mode-0600 ownership key;
- strict source invariance passed with 119 entries, 10 Git objects, two status
  records, and zero extension markers;
- the 72-file frozen production boundary is byte-for-byte equal to the
  independently audited candidate; and
- all exact gate-owned disposable container, network, and volume inventories
  returned zero after cleanup.

The original audit, independent re-audit, focused re-audit, and
single-finding re-audit FAIL decisions remain unchanged and correct for their
inspected revisions. This current PASS records later closure plus complete
local integration evidence; it is not a retroactive rewrite.

Remote CI, production deployment, hostile multi-tenant use, Customer 0, LLM
or Agents SDK behavior, and Git delivery/PR are **NOT VERIFIED** or explicitly
outside the Phase 4 implementation. No merge, fast-forward, push, pull
request, tag, Customer 0, CreativeDeploy, Phase 5, or production action is
authorized by this status.

Detailed evidence is in
[`docs/evidence/phase-4-final-integration-gate-verification.md`](../evidence/phase-4-final-integration-gate-verification.md).

## Independent budget re-audit decision

The Round 4 Blocking Medium finding **Expanded checkout manifest bypasses
configured entry budget** is **CLOSED**.

**CONFIRMED** by the independent current-worktree review:

- the unchanged permanent shared-tree reproduction passes `1/1`;
- a distinct single-file subtree referenced by three parent directories is
  charged once per expanded path;
- with limit `5`, a five-entry manifest succeeds exactly;
- the possible sixth entry returns typed `mirror_budget_exceeded` before the
  third shared blob read or digest;
- the recursive walk does not first construct an over-budget complete list;
- actual manager rejection creates no Workspace, registry, or ownership
  record, consumes no additional Permit, and preserves the mirror, source,
  and a sibling marker;
- the complete blocking file passes `13/13`;
- manifest/object closure focus passes `24/24`;
- source invariance passes with 119 entries, 10 Git objects, 2 status records,
  and 0 extension markers;
- Workspace security passes `63/63` plus static isolation;
- Runner/Protocol passes `83/83`; and
- final format, lint, and type checks pass.

The independent reviewer changed no production code. No new Critical, High,
or blocking Medium finding was discovered. Historical FAIL reports remain
unchanged.

This is not a Phase 4 Security Gate PASS. Aggregate `make verify`, Web E2E,
full Chaos, full Docker Gate, Customer 0, remote CI, integration, merge,
CreativeDeploy, and Phase 5 remain unexecuted and unauthorized. The only next
milestone is the single final Phase 4 integration gate.

## Round 4 remediation candidate

**CONFIRMED** in the current Round 4 worktree:

- source-less checkout-manifest construction now shares one expanded-entry
  count across recursive paths;
- each regular file, symlink, or inert gitlink atomically charges itself and
  every pending ancestor directory before content processing or construction;
  empty Git trees retain their existing omission semantics;
- equality with `mirror_max_tree_entries` is accepted, while the next entry
  raises typed `mirror_budget_exceeded`;
- shared trees are charged again for every distinct path, without first
  constructing an unbounded complete manifest;
- raw path bytes, entry type, Git mode, size, digest, symlink, inert gitlink,
  replacement metadata, exact closure, semantic proof, quarantine, source
  invariance, process-group timeout, discard, and Permit production logic are
  unchanged.

The permanent five-entry shared-tree reproduction failed twice before the
repair with `8 <= 5`, then passed unchanged after the repair. Five additive
budget regressions pass: the sixth entry is rejected before its blob is reread,
the exact four-entry semantic boundary succeeds and registers a Workspace,
and deep, wide, and repeated-subtree over-limit cases create no Workspace,
registry, or ownership record while preserving the mirror, source, and
sibling.

Current focused evidence passes:

- permanent shared-tree reproduction: `1/1`;
- additive budget regressions: `5/5`;
- complete blocking reproduction file: `12/12`;
- manifest/object-closure focus: `24/24`;
- source invariance: 119 entries, 10 Git objects, 2 status records, and 0
  extension markers;
- Workspace security: `63/63` plus static isolation;
- complete Runner/Protocol: `82/82`;
- repository format, lint, and typecheck;
- complete backend/Runner/Protocol tests: `160/160`, 81.79% coverage; and
- Web unit tests: `41/41`.

The first format check found only the new test file's Ruff layout. After that
scoped correction, the next format check found only the new ExecPlan's
Prettier layout. A later post-tightening check found only the updated evidence
document's Prettier layout. All three are preserved as non-behavioral first
failures; the final complete format check passes.

This is implementer evidence only. The historical Security Gate remains FAIL,
and Round 4 does not authorize `main` merge, Customer 0, CreativeDeploy,
Phase 5, remote, push, pull request, tag, delivery, or deployment.

## Independent single-finding re-audit decision

`VE-P4-FREAUD-001` remains **FAIL / REMEDIATION REQUIRED**.

Round 3 closes the original packed `refs/replace` reproduction:

- the unchanged original test passes `1/1`;
- a distinct independent scenario inserts packed replacement metadata after
  final mirror validation and before actual worktree checkout while hostile
  host Git environment variables try to redirect and re-enable Git behavior;
- the actual Workspace still contains the exact approved bytes, creates its
  registry, and the polluted mirror fails closed on the next prepare;
- the Round 3 replacement/manifest matrix passes `6/6`;
- the source/object/ref/manifest focus passes `19/19`;
- strict source invariance passes; and
- the Workspace/Protocol target passes `58/58` plus its static isolation
  check.

The required Workspace semantic proof has one new stable Blocking Medium
capacity defect. A shared Git subtree is charged once by the authorized object
walk but expanded once per path by the new checkout-manifest walk. With
`mirror_max_tree_entries=5`, production `prepare_mirror` returns an eight-entry
manifest rather than rejecting it. The permanent secure-expectation test fails
`8 <= 5` twice. The complete blocking file is `1 failed, 11 passed`, and the
complete Runner/Protocol target is `1 failed, 76 passed`; both have the same
sole failure.

The later descriptor-rooted Workspace scanner does reject this minimal case
with typed `mirror_budget_exceeded`, quarantines the checkout, removes its
canonical address, and creates no registry. No unauthorized registered
Workspace bytes were reproduced. The blocker is that compact shared-tree DAGs
can expand expected-manifest CPU/memory exponentially before that enforcement
point, threatening the declared bounded Runner and leaving incomplete mirror
state requiring manual recovery.

No production code was modified. No existing test was weakened, skipped, or
marked expected-failing. No customer repository was accessed. No remote,
push, merge, pull request, tag, delivery, deployment, or Phase 5 action
occurred.

## Round 3 remediation candidate

The audited Round 3 branch narrowly implements the production correction for
`VE-P4-FREAUD-001` / `VE-P4-AUD-001`:

- new mirrors use `git init --bare --template=` followed by exact managed
  config, a detached authorized `HEAD`, and an empty loose/packed ref
  namespace;
- existing mirrors fail closed unless top-level metadata, config, object
  layout, detached `HEAD`, and empty refs match the managed template;
- every Runner-owned Git process uses both `--no-replace-objects` and
  `GIT_NO_REPLACE_OBJECTS=1`; and
- the source-less parser's path/type/Git-mode/size/SHA-256 authorized checkout
  manifest must exactly match an independent descriptor-rooted no-follow
  Workspace manifest before ownership or registry creation. A mismatch is
  atomically isolated without recursive deletion.

The unchanged independent packed-replacement test now passes. The current
ordered local runs also pass the six-case additive replacement/manifest
matrix, complete ten-test blocking reproduction file, 19-case Git
object/ref/manifest focus, strict source invariance, 58-test Workspace/Protocol
security target plus static isolation check, and complete 75-test
Runner/Protocol suite.

The first Workspace security run is preserved as `57 passed, 1 failed`: the
existing ignored-inventory test assumed the default Git template created
`info/`. Its synthetic setup was corrected to create that parent before
injecting `info/exclude`; the discard quarantine assertions were unchanged and
the targeted/full reruns pass.

Repository-wide format, lint, and typecheck pass. Final `make test` passes
backend `153` tests at 81.79% coverage and Web `41` tests. The first two full
test attempts exposed a coverage-load race in the already passing
process-group audit fixture; a bounded child-ready/leader-exit handshake made
the fixture deterministic without changing production timeout logic or its
secure assertions. The complete blocking file then passes `10/10`.

This remains historical implementer evidence. The later independent
single-finding decision above is the governing result.

## Focused re-audit decision

The Round 2 candidate remains **Security Gate: FAIL**. Three named blocker
scopes pass current independent focused checks:

- `VE-P4-AUD-003`: authenticated discard proof;
- `VE-P4-AUD-005`: complete process-group deadline; and
- `VE-P4-AUD-002`: real-PostgreSQL Side-effect Permit closure.

`VE-P4-AUD-001` fails on new Critical finding `VE-P4-FREAUD-001`. An existing
managed mirror can encode `refs/replace` in `packed-refs`. Current validation
does not reject that representation and the Runner-owned Git subprocesses
interpret it. The exact authorized object-ID set and requested `HEAD` can
remain intact while checkout materializes another reachable commit's tree.
This violates the exact authorized revision boundary.

The corrected complete blocking-reproduction file produces
`1 failed, 9 passed`; the sole failure is the packed replacement secure
assertion. The complete Runner/Protocol focused files produce `52 passed`.
The real-PostgreSQL Workspace API file produces `13 passed`, including an
independent five-session convergence test. The strict source-invariance target
passes.

Because one Critical blocker is stable, the final full Gate, aggregate
`make verify`, full Docker isolation Gate, browser/E2E, smoke, chaos,
security, and Eval are **NOT VERIFIED** in this review. They were not run or
inferred after the stop condition.

No production code was modified. No customer repository was accessed. No
remote, push, merge, pull request, tag, delivery, deployment, or Phase 5 action
occurred.

## Preserved pre-focused governance status

The independent re-audit of the isolated security-repair commit completed with
**Security Gate: FAIL**. Three production defects are independently stable:

- `VE-P4-AUD-001` remains open because the source-less adapter copies an
  unreachable, unapproved source object into the Runner mirror.
- `VE-P4-AUD-003` remains open because registry/root absence without trusted
  signed pending-discard completion proof is reported as successful discard.
- `VE-P4-AUD-005` is a blocking Medium because a descendant that retains the
  output pipes can continue past the Git operation timeout after the process
  leader exits.

The first two defects are Critical and High; either alone requires FAIL. The
third is independently Gate-blocking within the declared local Runner
resource boundary. `VE-P4-AUD-002` is not independently closed because the
complete new concurrency/adversarial matrix was stopped after the Gate had
already failed. `VE-P4-AUD-004` and local `VE-P4-AUD-006` checks pass.

The original audit FAIL and the repair implementer's evidence remain preserved
history. Neither is rewritten as the current result.

## Round 2 remediation candidate

Round 2 locally implements the three production corrections required by the
independent re-audit:

- exact authorized commit/ancestor/tree/blob closure parsing and
  Runner-owned loose-object materialization, including bounded loose and
  packed OFS/REF delta input, without Git execution against the source;
- domain-separated signed pending/completed discard proof with exact
  registry, ownership, root device/inode, operation, Permit, Attempt, Lease,
  digest, and time-window binding; and
- monotonic complete-process-group monitoring after leader exit, with
  nonblocking pipes, bounded TERM/KILL escalation, reaping, and explicit
  termination failure.

The unchanged re-audit file now passes `7/7` locally. Additive Runner,
Protocol, source-invariance, and real-PostgreSQL Permit regressions also pass
their focused Round 2 runs. Every named non-aggregate local target, including
Docker, E2E `14/14`, both smoke targets, both chaos targets, security, and
Eval, has exited zero. Live Runner isolation was inspected in a uniquely
named disposable Compose project and its exact resources were removed.
The corrected complete post-documentation `make verify` rerun exited zero.
Final diff review then closed one further in-scope pack-directory enumeration
budget gap; focused, complete Runner/Protocol, and source-invariance reruns
pass, and the final post-correction aggregate rerun exited zero. Remote CI is
not run.

`VE-P4-AUD-002` received the previously missing real-PostgreSQL concurrency,
revocation, binding, crash-ordering, retry, lineage, and budget matrix. No new
production Permit defect was reproduced, so Round 2 does not change Permit
production code.

These are implementer-candidate facts only. The historical Security Gate
remains FAIL until a new independent focused re-audit makes a new decision.

## Preserved re-audit disposition

- `VE-P4-AUD-001`: **FAIL / UNRESOLVED.** Source registration and mirror
  preparation no longer invoke Git against the source, but object copying is
  not restricted to the authorized revision's reachable object closure.
- `VE-P4-AUD-002`: PostgreSQL-backed Side-effect Permits bind the current
  Runner, Job, Attempt, Lease, Grant, Workspace, operation and canonical
  digest, including the immutable authorization time window, immediately
  before prepare, create/replace, rollback, or discard.
  `revoke_requested` blocks new permits; effective `revoked` waits for
  in-flight permits to become terminal or expire. Focused real PostgreSQL
  evidence passes; complete independent closure is **NOT VERIFIED**.
- `VE-P4-AUD-003`: **FAIL / UNRESOLVED.** Registry payloads and ownership
  manifests are authenticated in normal paths, but absence of both registry
  and expected root can still return idempotent success without trusted signed
  pending-discard evidence.
- `VE-P4-AUD-004`: **PASS** for the independently executed strict synthetic
  source-invariance harness.
- `VE-P4-AUD-005`: **FAIL / BLOCKING MEDIUM.** Live Runner CPU, memory, PID,
  FD, rootfs, capability and network controls pass, but timeout/process-group
  enforcement does not.
- `VE-P4-AUD-006`: in-scope external Compose images use immutable digests and
  GitHub Actions use full commit SHAs. Local configuration is **PASS**; remote
  CI is **NOT VERIFIED**.

The API, database migration, pure Runner Protocol, generated OpenAPI/
TypeScript contract, browser surfaces, E2E/chaos harnesses, Make targets, CI
definition, threat models, architecture, ADRs, and runbooks remain part of the
historical first-repair candidate. This section records the independent
re-audit result at `b457b61`; it is intentionally not rewritten by Round 2.

## Product boundary

Implemented Phase 4 remains fixture-only Level 1:

- independently decided exact Execution Grant;
- opaque synthetic Repository Handle;
- closed prepare/list/read/create/replace/status/diff/rollback/discard jobs;
- descriptor-rooted bounded UTF-8 operations;
- immutable Checkpoints and initial-baseline rollback;
- Runner-only private mirror/workspace/registry/credential volumes; and
- outbound API-only Runner control transport.

Explicitly absent: LLM, OpenAI Agents SDK, Agent Trace, shell, arbitrary
subprocess, target repository command/build/test, delete/rename/binary tool,
source write, Git delivery, branch/commit/push/PR, remote CI evidence,
authentication, multi-tenancy, public hosting, and production deployment.

CreativeDeploy is not authorized for this repair and was not mounted,
accessed, read, written, built, tested, or cleaned.

## Preserved re-audit verification status

The current re-audit evidence includes stable minimal filesystem/process
reproductions, a strict independent source-invariance run, real PostgreSQL
migration and eight-test Workspace API execution, 35 focused
Runner/Protocol tests, contract drift checks, Compose rendering, live Docker
isolation inspection, and final production-boundary hash comparisons.

The three-test first run also exposed a missing audit-test exception import.
That test-only `NameError` is preserved, classified separately, corrected only
in the audit test, and rerun. The corrected complete test file produces
`3 failed, 4 passed`: the failures are the three intended secure assertions
against current production behavior.

Full Web/browser/E2E/smoke/chaos/security/Eval and aggregate `make verify` were
not continued because the Critical, High, and blocking Medium reproductions
already make Security Gate PASS impossible. They are **NOT VERIFIED** in the
current re-audit and are not inferred from repair evidence.

Exact commands, exit codes, counts, first failures, root causes, corrections,
runtime facts, and stopped-check rationale are in
`docs/evidence/phase-4-security-reaudit-verification.md`.

Round 2 commands, counts, production/source invariance, PostgreSQL ordering,
Docker evidence, and final Git state are recorded separately in
`docs/evidence/phase-4-security-remediation-2-verification.md`.

## Remaining limitations

- The direct packed-replacement exploit is denied, but the Round 3
  Workspace semantic proof does not enforce its expanded path-entry budget
  during expected-manifest construction. `VE-P4-FREAUD-001` remains open.
- The Permit, discard, and process-group scopes pass this focused review, but
  those historical local PASS results do not override the current
  manifest-capacity blocker.
- Python does not expose portable `openat2`/`renameat2` pathname-CAS; the
  implementation retains descriptor-rooted no-follow checks and a sole
  Runner-Writer assumption.
- Local bearer credentials, HMAC ownership, Docker networking, PostgreSQL
  polling, and synthetic fixtures are development controls, not hostile
  multi-tenant or production identity/isolation.
- No privileged garbage collector or automatic quarantine adjudication exists.
- Filesystem quotas, fleet admission, production credential lifecycle,
  backup/restore, incident response, and public deployment remain future work.

## Recommended next milestone

**Perform a narrow Phase 4 remediation that bounds every expanded
source-less checkout-manifest path before materialization, followed by another
fresh independent single-finding read-only re-audit of
`VE-P4-FREAUD-001`.**

Do not merge `main`, access CreativeDeploy/Customer 0, push, create a pull
request, or begin Phase 5 before a fresh independent PASS.

`SINGLE-FINDING RE-AUDIT COMPLETE — VE-P4-FREAUD-001 FAIL — REMEDIATION REQUIRED`
