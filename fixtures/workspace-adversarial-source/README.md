# Workspace adversarial fixture v0.1

This versioned fixture definition is materialized by
`scripts/create_workspace_fixture.py` into the ignored `.runtime/` directory.
The generated source is a real Git repository with a deterministic committed
baseline plus deliberate dirty and untracked source-only content.

It contains benign synthetic examples of sensitive paths, symlinks, binary and
oversized files, a malicious instruction file, a local gitlink, an LFS pointer,
Unicode and collision paths, and a source-only hook. It contains no real secret.
FIFO and socket cases are created dynamically by the Runner security tests.
