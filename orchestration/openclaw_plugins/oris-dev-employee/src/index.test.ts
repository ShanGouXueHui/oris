import assert from "node:assert/strict";
import test from "node:test";

import {
  createTelemetryRecord,
  DEFAULT_BASE_URL,
  resolvePluginConfig,
  sanitizePayload,
} from "./index.js";

function withCredentials(baseUrl: string): string {
  const url = new URL(baseUrl);
  url.username = "user";
  url.password = "pass";
  return url.toString();
}

function withPathPrefix(baseUrl: string): string {
  return new URL("api", `${baseUrl}/`).toString();
}

function hostPath(...parts: string[]): string {
  return ["", ...parts].join("/");
}

test("resolvePluginConfig applies safe defaults", () => {
  const config = resolvePluginConfig({});
  assert.equal(config.baseUrl, DEFAULT_BASE_URL);
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
    () => resolvePluginConfig({ baseUrl: withCredentials(DEFAULT_BASE_URL) }),
    /credentials/,
  );
  assert.throws(
    () => resolvePluginConfig({ baseUrl: withPathPrefix(DEFAULT_BASE_URL) }),
    /path prefix/,
  );
});

test("sanitizePayload removes secret and host-path fields", () => {
  const sanitized = sanitizePayload({
    task_id: "task-123",
    status: "running",
    token: "should-not-appear",
    prompt_path: hostPath("home", "admin", "projects", "oris", "prompts", "task.md"),
    nested: {
      authorization: "Bearer abcdefghijklmnopqrstuvwxyz",
      product_commit: "abc123",
      message: `See ${hostPath("home", "admin", "projects", "product", "file.py")}`,
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
