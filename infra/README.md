# Infrastructure Boundary

Local infrastructure is intentionally small. The executable stack is defined
in root `compose.yaml`; application images live beside `apps/api` and
`apps/web`.

`compose.e2e.yaml` mounts a generated adversarial Git fixture read-only into
the API for real-stack tests. `compose.customer0.yaml` optionally mounts only
the exact CreativeDeploy host path, only into the API, at the stable container
path `/repositories/customer0/creative-deploy` with `read_only: true`. The
host path must be provided at invocation and must not be committed. Web and
database services receive no target-repository mount.

No Kubernetes, cloud deployment, gateway, queue, or production secrets
configuration belongs here until a real requirement and approved ExecPlan
exist.
