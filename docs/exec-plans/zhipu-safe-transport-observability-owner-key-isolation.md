# Zhipu Safe Transport Observability and Owner-Key Isolation

Status: `IMPLEMENTED AND LOCALLY VERIFIED; REMOTE CI PENDING`

## Purpose and fixed authority

This maximum-safe batch begins from exact `main`
`a80efaf6509c9923ad60225412079f133a117066`. It may implement prospective,
type-based Provider transport classification, durable safe logging, deterministic
synthetic regressions, owner-key isolation, truthful failure evidence, one
corrective commit, an ordinary push, one Draft PR, and the naturally triggered
Fast and Heavy checks. It may not mark ready, merge, retry a live Provider call,
or authorize a second Zhipu canary.

The existing live Invocation with correlation `59bd943ccb99` is immutable
historical evidence. It remains `outcome_unknown` with
`transport_error / provider_transport_error`; the new classifier applies only to
future Invocations.

## Security contract

- Classify only concrete exception types, allowlisted cause/context wrapper
  types, and safe `errno` categories. Never inspect exception text or arguments.
- Never persist or log URLs, headers, Authorization, credentials, bodies,
  prompts, raw responses, or exception text.
- Preserve the dedicated connect/read and total-deadline timeout paths. A more
  precise error code does not make an ambiguous post-dispatch outcome definite.
- Keep retry and fallback at zero.
- The maintainer `ZHIPU_API_KEY` belongs only to the explicit local canary
  loader after every reviewed authorization gate. Product settings, Provider
  discovery, and ordinary planning may not read it or treat it as a user
  credential.
- Missing future user BYOK material means Provider unavailable and configure
  your own credential. This batch does not implement a BYOK vault.

## Screenshot evidence preservation

This batch must not create a Live Validation PASS image. If the existing real
Web Console safely projects the failed Invocation, capture one image clearly
classified `LIVE / outcome_unknown`; otherwise retain only the structured
record. Any future successful screenshot set must be read from one already
successful Invocation and must generate zero additional Provider requests.

## Work sequence

1. Verify exact root, Git identities and cleanliness, migration head, Provider
   enablement, and the unique live Zhipu row without reading Provider keys.
2. Create one corrective branch from the exact baseline.
3. Add the closed prospective classifier and fixed-field durable transport log.
4. Remove Provider owner credentials from general product settings and prove
   ordinary Zhipu planning cannot read or consume the canary credential.
5. Exercise the synthetic failure matrix, nested secret-negative surfaces,
   lifecycle, request count, retry/fallback, and governance invariants against
   one isolated PostgreSQL lifecycle.
6. Save truthful structured failure evidence and one safe failure screenshot if
   supported by the unchanged Web Console; validate the screenshot manifest
   exactly once.
7. Run changed-scope static and secret checks, then one backend canonical
   aggregate.
8. Seal one commit, push once, open one Draft PR, and wait for Fast and Heavy
   without reruns.

## Rollback

Before publication, delete only the uncommitted paths introduced by this branch
and restore edited paths from the exact baseline through a reviewed patch. After
publication, use a new revert commit; never rewrite the published branch or the
historical Invocation.

## Progress log

- Preflight: `VERIFIED` on the exact baseline. Local `HEAD`, local `main`,
  `origin/main`, remote live `main`, and expected main all matched. The worktree,
  index, untracked set, and stash were empty; no Git operation was active.
- Database: `VERIFIED` at Alembic `20260809_0016`. Exactly one live Zhipu
  Invocation exists, and it is the fixed failed attempt described above.
- Focused validation: `VERIFIED`, 184 passed and 1 deselected in one current-
  tree aggregate after corrective test-harness work. The 12-case transport
  matrix, nested secret-negative surfaces, fixed logging fields, no retry or
  fallback, governance zero-side-effect, ordinary disabled-Zhipu path, and
  owner-key read count zero all passed.
- Static and contracts: `VERIFIED`. Changed-scope Ruff format/check and mypy,
  generated OpenAPI contract drift, fail-closed secret scanner plus its
  dependency-failure regression, and `git diff --check` passed.
- Backend canonical: `VERIFIED ONCE`, 528 passed with 85.03% coverage. The one
  isolated PostgreSQL service was then stopped and removed.
- Screenshot preservation: the failed canary request includes canary-only
  fields that the unchanged ordinary AI Plan response schema rejects. Per the
  preservation contract, no UI was fabricated or modified for a failure image;
  screenshot count and screenshot-generated Provider request count are both
  zero. The structured failure record is retained instead.
- Remote Draft PR and Fast/Heavy identity: `NOT YET VERIFIED`.
