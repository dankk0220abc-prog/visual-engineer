# CreativeDeploy Phase 2 Discovery

## Proven committed-HEAD facts

The read-only Snapshot recorded:

- revision `bd2fcd23a004ccc99e45bafaef49fe444c1f70fb`;
- branch `main`;
- 86 tracked entries;
- 16 selected policy files and 70 skipped entries;
- 24,639 selected committed bytes;
- package manager `pnpm`;
- languages CSS, HTML, JavaScript, Python, and TypeScript;
- frameworks/signals FastAPI, React, Tailwind CSS, Testing Library, Vite, and
  Vitest;
- six detected test paths across API integration/unit and Web tests;
- no design-system signal under the scanner's current structural heuristics;
  and
- four committed repository instruction/readme files recorded only as
  untrusted path/hash/provenance metadata.

The scanner classified one instruction-file pattern as a permission-escalation
risk and skipped four known binary entries. These are conservative structural
findings, not evidence that a human instruction was malicious.

## Working-tree observation

The repository was dirty with 13 relative paths: four modified tracked paths
and nine untracked paths. The tracked diff stat was four files, 84 insertions,
and 21 deletions. Dirty and untracked file contents were not read and are not
part of the Snapshot facts or fingerprint.

## Limits of discovery

The scanner is deliberately bounded and does not read the full source tree.
No design-system signal from the current heuristics means “not confirmed,” not
“none exists.” Validation opportunities in the Plan are future typed steps;
no CreativeDeploy build, test, lint, browser, formatter, import, install, or
script ran.
