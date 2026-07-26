# Infrastructure Boundary

Foundation infrastructure is intentionally small. The executable local stack
is defined in the root `compose.yaml`; application image definitions live next
to `apps/api` and `apps/web`.

No Kubernetes, cloud deployment, gateway, queue, or production secrets
configuration belongs here until a real requirement and approved ExecPlan
exist.
