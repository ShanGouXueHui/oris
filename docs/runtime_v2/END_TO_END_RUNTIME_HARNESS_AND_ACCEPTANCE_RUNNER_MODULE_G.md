# Runtime v2 Module G - End-to-End Runtime Harness and Acceptance Runner

## Objective

Module G combines Modules B-F into deterministic acceptance scenarios that validate the runtime substrate as an integrated system.

## Scenarios

1. Success: run creation, queueing, worker execution, executor success, completion, evidence indexing.
2. Repair: retryable failure, repair path, completion.
3. Approval: high-risk action, approval request, approve decision, resumed execution, completion.
4. Blocked: high-risk action, reject decision, blocked state.

## Evidence

Each scenario writes a scenario summary and creates an evidence index using the Module E publisher.

## Boundary

Module G is still a deterministic local harness. It does not mutate product repositories, perform deployment, or call external services.
