# GitHub Publication Readiness

## Verdict

- First Private repository:
  `READY_FOR_EXPLICIT_PRIVATE_REPOSITORY_CREATION_AUTHORIZATION`.
- Public conversion: `BLOCKED`.
- Production/public deployment: not enabled and not authorized.
- Real AI Provider: not configured and not authorized.

The exact evidence and local exit codes are in
[GitHub Publication Readiness Verification](../evidence/github-publication-readiness-verification.md).

## Suggested repository identity

- Name: `visualengineer`
- Description: `Governed, human-approved frontend planning and fixture-only delivery evidence for enterprise teams.`
- Default branch: `main`
- Visibility for first publication: Private

Avoid descriptions that claim autonomous production delivery, real Provider
integration, external customers, performance improvements, or remote Git.

## Private first-publication checklist

- [x] Canonical English README and aligned Simplified Chinese README.
- [x] Architecture, Quick Start, deterministic fixture demo, Security,
      contribution, and License-decision entry points.
- [x] Current-tree and complete-history local secret scan with redacted output.
- [x] PII, local-path, internal/customer, binary, large-object, mode, symlink,
      LFS, generated-artifact, ignore-rule, and Docker-context review.
- [x] Fast and heavy GitHub Actions definitions with immutable action SHAs,
      minimal permissions, lockfile-bound caches, and no repository Secret.
- [x] Pull request and structured issue templates.
- [x] Dependabot configuration for Actions, Python, and pnpm/npm manifests.
- [x] Scoped local publication-readiness checkpoint, with hash reported in the
      final handoff.
- [ ] Owner creates the Private repository only after explicit authorization.
- [ ] Owner confirms repository owner/account and final name/description.
- [ ] Add the remote and push only under a separate explicit authorization.
- [ ] Observe real GitHub Actions and retain remote run URLs before claiming CI
      pass.
- [ ] Configure branch protection after actual check names are visible.

## Public conversion blockers

1. Choose and approve a License. Apache-2.0 is recommended but not adopted.
2. Curate local absolute paths from current files and reachable history.
3. Review all CreativeDeploy, Customer 0, discovery, acceptance, internal audit,
   and detailed security evidence for consent and disclosure suitability.
4. Confirm that the GitHub noreply author identity is intended to remain in
   public commit metadata.
5. Decide whether historical evidence remains in a public repository, moves to
   a private evidence archive, or is replaced by sanitized public summaries.
6. Configure a maintained private security intake route and response policy.
7. Decide public contribution terms and then adopt an appropriate Code of
   Conduct.
8. Run a fresh secret/PII/history scan after curation. Do not rewrite history
   without a separate reviewed plan, backup, exact target list, and explicit
   owner approval.

No confirmed real secret was found, so history rewriting is not currently
required for credential rotation. It may still be required for Public content
curation.

## Content classification

### Suitable for the first Private repository

- source, tests, migrations, generated OpenAPI/types, lockfiles, and synthetic
  fixtures;
- governance ADRs, ExecPlans, verification evidence, and independent audit
  history under restricted repository access;
- internal Customer 0 material already committed, pending Public curation; and
- local development defaults containing only documented synthetic values.

### Must be removed or sanitized before Public

- private-machine absolute paths in current and historical evidence;
- customer/design-partner discovery, constraints, acceptance material, and
  repository-specific facts without explicit disclosure approval;
- audit details that reveal unnecessary local topology or sensitive defensive
  implementation detail; and
- any screenshot or recording with account, browser-profile, host, or customer
  information. No such tracked media was found in this review.

### Never commit

- real `.env`, API key, token, password, private key, certificate, cookie,
  session, cloud/database/registry credential, or secret-store export;
- real customer source, database, dump, backup, address, phone, personal
  email, or account data;
- `.runtime`, PostgreSQL data, caches, `node_modules`, `.venv`, `.next`, logs,
  coverage, Playwright reports/results, traces, screenshots/videos from real
  accounts, or built release artifacts; and
- a real Provider configuration or credential until a separately reviewed
  credential and network design exists.

## Recommended branch protection

After the first remote workflows run and actual check names are confirmed:

- require pull requests for `main`;
- require at least one approving review and dismiss stale approvals for
  security/authority changes;
- require conversation resolution;
- require the stable fast checks and selected heavy verification checks;
- require branches to be up to date or use a merge queue if later adopted;
- require linear history;
- block force pushes and branch deletion; and
- restrict bypass to explicitly named administrators/emergency roles.

Never make a check required until its remote name and reliability are observed.

## Actions and fork policy

Workflow-level permission is only `contents: read`; no job grants write,
`id-token`, packages, deployments, issues, pull requests, or security-event
permission. Workflows use `pull_request`, never `pull_request_target`, and read
no repository Secret. Keep GitHub's fork settings at read-only token, do not
send Secrets or write tokens to fork workflows, and require approval for
untrusted private-fork runs.

Every external action is pinned to a 40-character commit SHA with a version
comment. Node, pnpm, Python, uv, PostgreSQL images, and project dependencies are
pinned or lockfile-resolved. pnpm and uv cache inputs are bound to
`pnpm-lock.yaml` and `uv.lock` respectively.

Failure artifacts are not uploaded by default. This avoids publishing tokens,
database state, source paths, or customer data. Add a future artifact only
after defining a synthetic allowlist and retention policy.

References:

- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub fork workflow permissions](https://docs.github.com/en/rest/actions/permissions)
- [GitHub dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)

## Dependency updates

Dependabot is prepared for weekly updates to GitHub Actions, the root Python
project, and the root pnpm workspace. Review lockfile changes, generated
contracts, release notes, licenses, and security advisories. Do not auto-merge
dependency PRs, especially for actions, execution boundaries, database
drivers, browsers, or container images.

## Release and tag strategy

- No tag or GitHub Release is authorized in the first publication step.
- After a release policy exists, use reviewed SemVer tags and release notes
  derived from exact commits and verified evidence.
- Protect tags or use a release environment before any future signed artifact
  publication.
- GitHub Pages, public hosting, package publishing, container publishing, and
  deployment remain disabled.

## Future real Provider secret configuration

A real Provider requires a new ADR and independent security review covering
credential ownership, repository/environment scoping, minimal permission,
egress allowlisting, log redaction, rotation, revocation, fork behavior,
approval separation, cost budgets, and Provider-specific evaluation. Store
credentials in a GitHub Environment or external secret manager only after that
design is approved. Never place a Provider key in `.env.example`, repository
Secrets available to fork PRs, workflow YAML, issue, PR, log, screenshot, or
artifact.
