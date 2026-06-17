import assert from "node:assert/strict";
import test from "node:test";

import {
  createTelemetryRecord,
  resolvePluginConfig,
  sanitizePayload,
} from "./index.js";

test("resolvePluginConfig applies safe defaults", () => {
  const config = resolvePluginConfig({});
  assert.equal(config.baseUrl, "http://127.0.0.1:18891");
  assert.equal(config.requestTimeoutMs, 5_000);
  assert.equal(config.telemetryEnabled, true);
  assert.equal(config.telemetryMaxBytes, 5_242_880);
  assert.match(config.telemetryPath, /\.local\/state\/oris\/openclaw-plugin\/latency\.jsonl$/);
});

test("resolvePluginConfig rejects non-loopback and credential-bearing URLs", () => {
  assert.throws(
    () => resolvePluginConfig({ baseUrl: "https://example.com" }),
    /loopback HTTP|loopback/,
  );
  assert.throws(
    () => resolvePluginConfig({ baseUrl: "http://user:pass@127.0.0.1:18891" }),
    /credentials/,
  );
  assert.throws(
    () => resolvePluginConfig({ baseUrl: "http://127.0.0.1:18891/api" }),
    /path prefix/,
  );
});

test("sanitizePayload removes secret and host-path fields", () => {
  const sanitized = sanitizePayload({
    task_id: "task-123",
    status: "running",
    token: "should-not-appear",
    prompt_path: "/home/admin/projects/oris/prompts/task.md",
    nested: {
      authorization: "Bearer abcdefghijklmnopqrstuvwxyz",
      product_commit: "abc123",
      message: "See /home/admin/projects/product/file.py",
    },
  }) as Record<string, unknown>;

  assert.equal(sanitized.task_id, "task-123");
  assert.equal(sanitized.status, "running");
  assert.equal("token" in sanitized, false);
  assert.equal("prompt_path" in sanitized, false);
  const nested = sanitized.nested as Record<string, unknown>;
  assert.equal("authorization" in nested, false);
  assert.equal(nested.product_commit, "abc123");
  assert.equal(nested.message, "See <redacted-path>");
});

test("createTelemetryRecord hashes identifiers and excludes content", () => {
  const record = createTelemetryRecord("model_call_ended", {
    durationMs: 1234,
    outcome: "success",
    provider: "example-provider",
    model: "example-model",
    runId: "run-secret-id",
    callId: "call-secret-id",
    sessionKey: "session-secret-id",
    prompt: "must not be recorded",
    response: "must not be recorded",
  });

  assert.equal(record.durationMs, 1234);
  assert.equal(record.outcome, "success");
  assert.equal(record.provider, "example-provider");
  assert.equal(record.model, "example-model");
  assert.equal(record.runHash?.length, 64);
  assert.equal(record.callHash?.length, 64);
  assert.equal(record.sessionHash?.length, 64);
  const serialized = JSON.stringify(record);
  assert.equal(serialized.includes("run-secret-id"), false);
  assert.equal(serialized.includes("call-secret-id"), false);
  assert.equal(serialized.includes("session-secret-id"), false);
  assert.equal(serialized.includes("must not be recorded"), false);
});
