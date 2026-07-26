# Evaluation Strategy v0

## Purpose

Evaluation must determine whether VisualEngineer is correct, safe, useful, and
recoverable, not merely whether it produces plausible text. Foundation starts
with deterministic API and browser smoke cases. There is no LLM benchmark,
production dataset, historical score, or Agent leaderboard yet.

Evaluation is scoped to the three V1 frontend delivery packages: Design
Implementation, Design-System Migration, and Frontend Quality Remediation.
Future cases must identify both the delivery package and the versioned customer
Deployment Pack used.

## Evaluation layers

1. **Deterministic contract checks:** input validation, errors, idempotency,
   request IDs, pagination, persistence, and migrations.
2. **Component behavior:** API services, frontend states, accessibility, and
   generated contract use.
3. **Real-stack smoke:** browser to web to API to PostgreSQL, including refresh
   persistence on desktop and narrow viewport.
4. **Future repository fixtures:** controlled repositories for investigation,
   prompt injection, permissions, changes, validation, and rollback.
5. **Future expert review:** blinded rubric assessment of requirement
   understanding, plan quality, code, design fidelity, and evidence.

## Future dimensions

| Dimension                         | Example measure                                                                    |
| --------------------------------- | ---------------------------------------------------------------------------------- |
| Requirement understanding         | Required constraints recalled; contradictions and ambiguity identified.            |
| Repository investigation accuracy | Cited fact precision/recall; unsupported claim count.                              |
| Plan quality                      | Correct dependencies, risks, verification, rollback, and scope.                    |
| Tool selection                    | Minimum sufficient tool/permission; invalid action attempts.                       |
| Permission adherence              | Unauthorized read/write/execute/egress attempts; approval binding.                 |
| Code correctness                  | Acceptance behavior, static checks, regression count.                              |
| Test pass rate                    | Required checks passed without weakened assertions or skips.                       |
| Visual consistency                | Token/component/layout delta against an approved reference.                        |
| Responsive behavior               | Critical flow success at defined viewport/content sizes.                           |
| Accessibility                     | Automated violations plus keyboard/screen-reader task success.                     |
| Repair success rate               | Valid failures fixed within bounded attempts without regression.                   |
| Rollback success rate             | State and worktree restored to checkpoint with evidence.                           |
| Token and cost                    | Input/output/cache tokens and currency per successful run.                         |
| Latency                           | End-to-end and per-state/tool percentiles.                                         |
| Human interventions               | Clarifications, approvals, rescues, and manual fixes per run.                      |
| Failure classification            | Product, model, policy, tool, environment, test, integration, and rollback causes. |
| Approval-to-PR time               | Elapsed time from exact plan approval to reviewable pull request.                  |
| First full-pass rate              | Runs passing every required validation before any repair.                          |
| CI pass rate                      | Required remote checks passing for submitted pull requests.                        |
| PR acceptance                     | Accepted or merged pull requests under a declared review policy.                   |
| Actual adoption                   | Active teams, repositories, and completed governed tasks over a defined period.    |

Scores must include evaluator version, dataset revision, run configuration,
sample count, confidence/uncertainty, failure taxonomy, and evidence references.
Never report a score from a prompt example or fabricated run.
No Foundation result establishes a production baseline, improvement
percentage, external adoption, or customer return on investment.

## Foundation dataset

`evals/datasets/foundation-smoke.jsonl` contains deterministic scenario
definitions, not runtime results. Cases cover:

- a legal local-path metadata task;
- a legal GitHub metadata task;
- invalid blank/over-limit/enum/NUL fields;
- equivalent idempotent replay;
- conflicting idempotency reuse;
- missing task retrieval;
- list order and pagination bounds;
- request-ID and database-readiness behavior.

Expected values are stable HTTP behavior and semantic assertions. Runtime tests
may adapt IDs/timestamps but must not loosen the outcome.

## Dataset hygiene

- Use synthetic repositories, IDs, names, and objectives.
- Include no personal path, production URL, token, or secret.
- Version cases in Git and review semantic changes.
- Keep train/development and held-out evaluation repositories separate once LLM
  work begins.
- Store failure artifacts under ignored paths and link only sanitized summaries.
- Do not tune prompts against every held-out case.

## Foundation release gate

Foundation passes evaluation only if all deterministic required cases have
executable tests, the real PostgreSQL/browser smoke succeeds, serious/critical
accessibility findings meet the declared policy, no unauthorized repository
access occurs, and verification evidence is recorded. Test definitions alone
do not satisfy the gate.

## Future benchmark work

The next evaluation milestone should build small adversarial, non-sensitive
fixture repositories with ground-truth file maps, injected malicious
instructions, ambiguous requirements, broken tests, responsive/accessibility
defects, and reversible changes. It should establish baseline human and
deterministic-agent results before introducing LLM scoring.
