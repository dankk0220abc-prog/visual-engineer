# CreativeDeploy Phase 2 Acceptance Criteria

The Customer 0 read-only case is accepted only when:

1. the API container runs non-root;
2. the exact CreativeDeploy mount reports `RW=false`;
3. Web and database services have no CreativeDeploy mount;
4. the scanner allowlist is the exact stable container repository root;
5. Snapshot revision equals the before/after committed `HEAD`;
6. branch, full porcelain status, and diff stat are identical before/after;
7. repository facts and instruction metadata contain no source corpus, secret,
   dirty content, untracked content, or host home path;
8. the Plan source is `deterministic_policy`;
9. Plan fingerprint equals the Snapshot fingerprint;
10. `execution_available` is false;
11. the Audit Timeline ends at `plan_submitted`;
12. Run is `awaiting_plan_approval` and Plan is `awaiting_approval`; and
13. no approve/reject request or target command/write occurs.

These criteria prove only the local Phase 2 governed read-only workflow. They
do not prove production safety, external-customer value, or delivery outcomes.
