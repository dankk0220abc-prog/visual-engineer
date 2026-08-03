## Summary

Describe the problem, the exact scope, and the resulting behavior.

## Governance and security impact

- Authority boundary changed: no / yes — explain
- Persistence or migration changed: no / yes — explain
- Protocol or generated contract changed: no / yes — explain
- Provider, network, credential, remote Git, or deployment changed: no / yes — explain

## Verification

List only commands run against this revision, with exit codes and material
limitations.

```text
command — exit code
```

## Checklist

- [ ] The change is narrowly scoped and unrelated work is preserved.
- [ ] No secret, real `.env`, PII, customer material, private host path,
      database, log, trace, browser artifact, or build output is included.
- [ ] Tests cover changed behavior and rejection/permission paths where
      relevant.
- [ ] Generated contracts follow source changes; migrations are additive.
- [ ] Documentation and evidence distinguish implemented, verified, planned,
      blocked, and not verified claims.
- [ ] Plan or Review approval is not described as execution, Git, or deployment
      authority.
- [ ] Screenshots, if any, contain only synthetic data and no account or browser
      profile information.
- [ ] No remote CI pass, production readiness, customer outcome, or Provider
      capability is claimed without direct evidence.

## Remaining limitations

State what is intentionally unchanged, blocked, or not verified.
