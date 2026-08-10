# Zhipu response-path safe classification remediation

Status: `IMPLEMENTED AND LOCALLY VERIFIED; REMOTE CI PENDING`

## Purpose and authority

This remediation starts from exact `main`
`992bc9cba5a3ad300cc63d9d926255b5eb6bab9a` at Alembic
`20260809_0016`. It may change only prospective response-path classification,
focused synthetic tests, and truthful Evidence. It must not read a real
Provider key, send another live Provider request, rewrite either historical
Invocation, change the Provider request/network/TLS/deadline/retry contract,
add a migration, mark a pull request ready, or merge.

The controlled branch is
`codex/fix-zhipu-response-path-classification`. The two immutable historical
Zhipu correlations are `59bd943ccb99` and `b7e92fd81760`; both remain
`live / outcome_unknown / transport_error / provider_transport_error`.

## Contract decisions

- No migration is required. Existing bounded `error_category` and fixed
  `error_code` fields express the prospective taxonomy.
- The adapter distinguishes a send that has not returned a response from body
  consumption after status and headers exist. It parses a fully consumed body
  only after that boundary.
- Every non-success HTTP status has a closed non-transport classification.
  Reviewed special 4xx meanings remain; other 4xx use request rejection, 5xx
  use upstream server error, and unexpected 1xx/3xx use invalid response.
- Response decoding, stream state, local/general/remote protocol failures,
  response read interruption, and an unknown body-iterator exception use
  bounded fixed codes. The true pre-response unknown fallback remains
  `provider_transport_error`.
- Post-dispatch transport ambiguity remains `outcome_unknown`; definite HTTP,
  response-budget, JSON/envelope, and typed validation failures retain their
  existing definite lifecycle.
- Endpoint, request body, Accept-Encoding, streaming mode, 64 KiB canary cap,
  timeout/deadline, client lifetime, TLS, semaphore, retry zero, and fallback
  zero remain unchanged.

## Work sequence

1. Fail closed on repository identity, Git cleanliness/operation state,
   database health, Alembic head, and exact historical Invocation facts.
2. Create one branch from the exact baseline and record immutable row
   fingerprints for final read-only comparison.
3. Split the response control-flow boundary and add the closed classifier.
4. Convert deterministic cases A-L into durable focused regressions, add the
   response-stage uniqueness assertion, complete HTTP-status sweep, protocol
   cases, and nested secret-negative Evidence surfaces.
5. Run one changed-risk focused batch, one backend canonical aggregate, and
   only necessary changed-scope static/secret checks.
6. Re-read the two historical rows, seal one implementation commit, push once,
   open one Draft PR, and wait for exact Fast/Heavy CI without reruns.

## Progress log

- Preflight: `VERIFIED`. Authoritative root, local/remote `main`, `HEAD`, and
  `origin/main` matched the required SHA. Worktree/index/untracked state was
  clean and no Git operation was active.
- Database: `VERIFIED`. Compose PostgreSQL was healthy, Alembic current/head
  were `20260809_0016`, Zhipu live count was exactly two, succeeded count was
  zero, and both immutable rows matched the authorized historical facts.
- Implementation: `VERIFIED`. No migration or network-contract change was
  required. Send, post-header body, and completed-body parse boundaries now
  retain distinct fixed classifications.
- Focused validation: the first aggregate exposed only test-harness construction
  and logger-capture defects (`175 passed / 12 failed`). After correcting that
  first root cause, the same aggregate passed `187/187`.
- Backend canonical: `VERIFIED ONCE`; `make test-api` passed `553/553` with
  `85.10%` coverage.
- Static/contract/security: changed-scope Ruff format/check, mypy over 145
  source files, OpenAPI contract drift, fail-closed secret scan, and
  `git diff --check` passed. The new Evidence Markdown required one mechanical
  Prettier correction before its final check.
- Historical evidence: `VERIFIED UNCHANGED` after validation. Zhipu live count
  remained two, succeeded count remained zero, and both immutable row
  fingerprints matched preflight.
- Commit, Draft PR, and exact Fast/Heavy CI: `NOT YET VERIFIED`.

## Rollback

Before publication, reverse only the paths changed on this branch through a
reviewed patch. After publication, use a new revert commit. Never reset, clean,
force-push, rewrite migration history, alter the two live Invocation rows, or
move `main`.
