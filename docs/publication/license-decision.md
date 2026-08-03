# License Decision Record

- Status: `DECISION_REQUIRED_BEFORE_PUBLIC`
- Scope: repository-wide source, documentation, fixtures, generated contracts,
  and future external contributions
- Current legal posture: no open-source license granted

## Decision needed

Private GitHub creation does not require an open-source license and is not
blocked by the current absence of a `LICENSE` file. Public conversion is
blocked until the repository owner chooses and approves an explicit legal
posture.

## Options

### Apache License 2.0 — recommended

Advantages:

- permissive use and distribution;
- explicit patent license and patent-termination terms;
- established notice and contribution language; and
- a good fit for enterprise-facing infrastructure where patent clarity is
  useful.

Costs:

- longer and more procedural than MIT;
- requires preserving the license and applicable notices; and
- the owner must confirm contributor and third-party material can be licensed
  on these terms.

### MIT License

Advantages:

- short, familiar, and permissive;
- low compliance overhead; and
- broad ecosystem recognition.

Costs:

- no equally explicit patent grant; and
- still requires an owner-approved copyright holder/year decision and review
  of all included material.

### No public license / all rights reserved

Advantages:

- preserves maximum control while product, customer material, and governance
  evidence are still being curated; and
- avoids granting rights before ownership and contribution policy are settled.

Costs:

- a Public repository without a license is visible source, not open source;
- external reuse and contribution terms remain unclear; and
- public collaboration should remain closed or individually negotiated.

## Recommendation and approval gate

Recommend Apache-2.0 after the owner confirms source ownership, third-party and
generated-file notices, contributor terms, and the intended copyright holder.
This recommendation is not approval. Do not add a formal `LICENSE` file or
describe the project as open source until the owner makes that decision.
