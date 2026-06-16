# Conversational Browser Acceptance — 2026-06-17

## Result

`PASS`

## Public entry

`https://control.orisfy.com`

## Operator-observed acceptance

- Landing page title: `ORIS AI 开发员工`
- Primary interaction: natural-language chat
- Engineering form fields hidden from the normal user
- `帮助` returned a natural-language explanation of supported development requests
- `查看进度` returned that the current session had no task
- No task card was created
- No product task was submitted
- No HTTP 403 remained on chat message submission

## Supporting server evidence

Public chat POST repair evidence commit:

`6e992978146bd8686d450638753acad098d22fc0`

The effective Nginx route now permits only the authenticated chat message POST while preserving the existing read-only restrictions on other engineering endpoints.

## Next acceptance stage

Submit one controlled real product goal through the conversation UI. Verify:

1. OpenClaw/Harness derives the intended project and objective;
2. ORIS creates exactly one task and renders a task card;
3. bridge/Codex executes the task;
4. progress can be requested conversationally;
5. tests, product commit, remote SHA, ORIS evidence and completed state are surfaced to the operator;
6. no ORIS platform code is written into the product repository and no product code is written into the ORIS repository.
