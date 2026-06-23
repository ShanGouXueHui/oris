# Runtime v2 Module E - GitHub Evidence Publisher and Run Evidence Index

## Objective

Module E makes ORIS runtime progress auditable from GitHub by generating deterministic evidence indexes and publish plans.

## Evidence Index Contract

An evidence index aggregates module artifacts and records:

- module name;
- status;
- artifact path;
- artifact SHA-256;
- artifact size;
- optional commit SHA.

The schema is stored in `schemas/runtime_v2/evidence_index.schema.json`.

## Publish Plan Contract

A publish plan records:

- target branch;
- commit message;
- files to publish;
- evidence index reference;
- optional issue update payload.

The schema is stored in `schemas/runtime_v2/github_publish_plan.schema.json`.

## Determinism

The evidence index id is derived from module name and artifact hashes. It is stable for the same artifact set even when input order changes.

## GitHub Boundary

Module E does not directly call GitHub APIs. It prepares auditable local contracts that ORIS or a GitHub connector can apply later. This keeps the runtime substrate testable without credentials.

## Non-Goals

- No credential handling.
- No direct GitHub API mutation.
- No product repository mutation.
- No deployment workflow.
