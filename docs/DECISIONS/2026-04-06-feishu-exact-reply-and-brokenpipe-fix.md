# 2026-04-06 Feishu exact-reply and BrokenPipe fix

## Decision
- Extend Feishu exact-reply patterns to support both colon and colonless forms:
  - 请只回答：pong
  - 请只回答pong
  - 只回答pong
  - 请只回复pong
  - 请只输出pong
- Suppress BrokenPipeError / ConnectionResetError in the Feishu callback server response writer.

## Why
- Real production traffic already enters the ORIS direct webhook path.
- The remaining defect was rule precision for colonless exact-reply prompts.
- BrokenPipeError was log noise from client-side disconnect timing and should not pollute production logs.

## Result
- Exact-reply becomes more robust for real user phrasing.
- Callback server logs become cleaner while preserving normal behavior.
