# VisualEngineer Runner Protocol

This package is the versioned, transport-neutral contract shared by the
VisualEngineer Control Plane and Local Runner.

It intentionally contains only Pydantic schemas, enums, protocol constants,
canonical serialization, permission-policy hashing, typed results, redaction
validation, and stable error codes. It must not import FastAPI, SQLAlchemy,
database code, API services, Runner executors, or filesystem helpers.
