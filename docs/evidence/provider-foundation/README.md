# Provider Foundation Evidence Workflow

This directory contains a minimal, reproducible local evidence set for the
model-neutral Provider foundation. Every image is synthetic Fixture/Mock
evidence and is not a live-provider call.

Capture against the repository-owned real API/Web/PostgreSQL stack:

```sh
CAPTURE_PROVIDER_EVIDENCE=1 ./scripts/run-e2e.sh provider-foundation.spec.ts
uv run python scripts/check_provider_evidence_safety.py --images-only
uv run python scripts/build_provider_evidence_manifest.py --redaction-scan-status passed
uv run python scripts/check_provider_evidence_safety.py
```

The Playwright capture step scans the exact visible DOM before each PNG is
written. It rejects credential-shaped text, authentication material, provider
environment values, and local home-directory paths. The post-capture scanner
then validates the five PNGs, their capture-time records, the manifest, and the
absence of provider environment values without printing any value.

Provider Evidence runs only in the dedicated
`provider-evidence-desktop-chromium` and
`provider-evidence-narrow-chromium` projects. Both projects fix `retries=0` and
turn trace, automatic screenshots, and video off. A safe reporter converts any
potentially sensitive test failure to a fixed code after clearing the page; it
never forwards the received DOM or underlying error. The synthetic-leak harness
launches a separate real Chromium process with the same zero-artifact policy,
expects a non-zero child exit, and proves that its output directory is absent or
empty.

The two selector images also exercise adversarial DOM tampering: a disabled
real Provider is force-selected, the API rejects the request, no AI Plan is
persisted, and the visible error remains explicitly classified as non-live.
