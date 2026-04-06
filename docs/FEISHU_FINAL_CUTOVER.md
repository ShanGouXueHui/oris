# Feishu Final Cutover

## Public endpoints
- https://control.orisfy.com/oris-api/v1/feishu/health
- https://control.orisfy.com/oris-api/v1/feishu/events

## Local service
- systemd user service: oris-feishu-callback.service
- local bind: 127.0.0.1:8790

## Execution mode
Feishu direct path is now configured for real send execution by default through the worker path.

## Required console-side settings
In Feishu developer console:
1. switch event subscription mode to developer server / webhook
2. set callback URL to:
   https://control.orisfy.com/oris-api/v1/feishu/events
3. set verification token to the value stored in:
   ~/.openclaw/secrets.json -> channels.feishu.verificationToken
4. subscribe the message receive event you need, typically:
   im.message.receive_v1

## Runtime note
Because this is now direct webhook mode, ORIS should be treated as the primary receiver for that Feishu app's event flow.

## Verification status
Feishu webhook URL verification has passed. The next step is real message event testing with `im.message.receive_v1` and end-to-end reply validation.

## Product routing principle
Current product principle: correctness first, latency second. Default general chat should prefer the strongest suitable general path rather than forcing a Chinese-model path by language alone.
