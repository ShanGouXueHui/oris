import { createHash } from "node:crypto";
import { appendFile, mkdir, rename, stat, unlink } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, resolve } from "node:path";

import { Type } from "typebox";
import {
  buildJsonPluginConfigSchema,
  definePluginEntry,
} from "openclaw/plugin-sdk/plugin-entry";

const DEFAULT_BASE_URL = "http://127.0.0.1:18891";
const DEFAULT_TIMEOUT_MS = 5_000;
const DEFAULT_TELEMETRY_PATH = "~/.local/state/oris/openclaw-plugin/latency.jsonl";
const DEFAULT_TELEMETRY_MAX_BYTES = 5_242_880;
const MAX_RESPONSE_BYTES = 1_000_000;
const MAX_TOOL_TEXT_BYTES = 32_000;
const TASK_ID_RE = /^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,120}$/;

export type ResolvedPluginConfig = {
  baseUrl: string;
  requestTimeoutMs: number;
  telemetryEnabled: boolean;
  telemetryPath: string;
  telemetryMaxBytes: number;
};

type JsonObject = Record<string, unknown>;

type TelemetryRecord = {
  timestamp: string;
  event: "model_call_ended" | "after_tool_call" | "agent_end";
  durationMs?: number;
  outcome?: string;
  success?: boolean;
  error?: boolean;
  provider?: string;
  model?: string;
  toolName?: string;
  runHash?: string;
  callHash?: string;
  sessionHash?: string;
};

const configSchema = buildJsonPluginConfigSchema(
  {
    type: "object",
    additionalProperties: false,
    properties: {
      baseUrl: {
        type: "string",
        default: DEFAULT_BASE_URL,
      },
      requestTimeoutMs: {
        type: "integer",
        minimum: 500,
        maximum: 30_000,
        default: DEFAULT_TIMEOUT_MS,
      },
      telemetryEnabled: {
        type: "boolean",
        default: true,
      },
      telemetryPath: {
        type: "string",
        default: DEFAULT_TELEMETRY_PATH,
      },
      telemetryMaxBytes: {
        type: "integer",
        minimum: 65_536,
        maximum: 52_428_800,
        default: DEFAULT_TELEMETRY_MAX_BYTES,
      },
    },
  },
  { cacheKey: "oris-dev-employee:config:v1" },
);

function asObject(value: unknown): JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonObject)
    : {};
}

function numberOrUndefined(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) && value >= 0
    ? value
    : undefined;
}

function stringOrUndefined(value: unknown, maxLength = 160): string | undefined {
  if (typeof value !== "string" || value.length === 0) {
    return undefined;
  }
  return value.slice(0, maxLength);
}

function booleanOrUndefined(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined;
}

function hashIdentifier(value: unknown): string | undefined {
  if (typeof value !== "string" || value.length === 0) {
    return undefined;
  }
  return createHash("sha256").update(value).digest("hex");
}

function expandHome(value: string): string {
  if (value === "~") {
    return homedir();
  }
  if (value.startsWith("~/")) {
    return resolve(homedir(), value.slice(2));
  }
  return resolve(value);
}

function resolveLoopbackBaseUrl(value: unknown): string {
  const candidate = typeof value === "string" && value.trim() ? value.trim() : DEFAULT_BASE_URL;
  const parsed = new URL(candidate);
  const host = parsed.hostname.toLowerCase();
  if (parsed.protocol !== "http:") {
    throw new Error("ORIS plugin baseUrl must use loopback HTTP");
  }
  if (!new Set(["127.0.0.1", "localhost", "::1"]).has(host)) {
    throw new Error("ORIS plugin baseUrl must resolve to loopback");
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error("ORIS plugin baseUrl must not contain credentials, query or fragment");
  }
  if (parsed.pathname !== "/" && parsed.pathname !== "") {
    throw new Error("ORIS plugin baseUrl must not contain a path prefix");
  }
  return parsed.origin;
}

export function resolvePluginConfig(raw: unknown): ResolvedPluginConfig {
  const config = asObject(raw);
  const requestTimeoutMs =
    typeof config.requestTimeoutMs === "number" && Number.isInteger(config.requestTimeoutMs)
      ? config.requestTimeoutMs
      : DEFAULT_TIMEOUT_MS;
  const telemetryMaxBytes =
    typeof config.telemetryMaxBytes === "number" && Number.isInteger(config.telemetryMaxBytes)
      ? config.telemetryMaxBytes
      : DEFAULT_TELEMETRY_MAX_BYTES;
  if (requestTimeoutMs < 500 || requestTimeoutMs > 30_000) {
    throw new Error("requestTimeoutMs outside allowed range");
  }
  if (telemetryMaxBytes < 65_536 || telemetryMaxBytes > 52_428_800) {
    throw new Error("telemetryMaxBytes outside allowed range");
  }
  const telemetryPath =
    typeof config.telemetryPath === "string" && config.telemetryPath.trim()
      ? config.telemetryPath.trim()
      : DEFAULT_TELEMETRY_PATH;
  return {
    baseUrl: resolveLoopbackBaseUrl(config.baseUrl),
    requestTimeoutMs,
    telemetryEnabled: config.telemetryEnabled !== false,
    telemetryPath: expandHome(telemetryPath),
    telemetryMaxBytes,
  };
}

const FORBIDDEN_KEY_RE =
  /(token|password|secret|authorization|credential|api.?key|cookie|header|prompt|content|environment|env|workdir|codex|private|absolute.?path|^path$)/i;
const ABSOLUTE_PATH_RE = /\/(?:home|root|etc|var|opt|srv|tmp)\/[A-Za-z0-9._~!$&'()+,;=:@%\/-]+/g;
const BEARER_RE = /Bearer\s+[A-Za-z0-9._~+\/-]+/gi;

export function sanitizePayload(value: unknown, depth = 0): unknown {
  if (depth > 8) {
    return "<max-depth>";
  }
  if (value === null || typeof value === "boolean" || typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    return value
      .replace(BEARER_RE, "Bearer <redacted>")
      .replace(ABSOLUTE_PATH_RE, "<redacted-path>")
      .slice(0, 1_000);
  }
  if (Array.isArray(value)) {
    return value.slice(0, 100).map((item) => sanitizePayload(item, depth + 1));
  }
  if (typeof value === "object") {
    const output: JsonObject = {};
    for (const [key, child] of Object.entries(value as JsonObject).slice(0, 100)) {
      if (FORBIDDEN_KEY_RE.test(key)) {
        continue;
      }
      output[key] = sanitizePayload(child, depth + 1);
    }
    return output;
  }
  return String(value).slice(0, 200);
}

function boundedToolText(value: unknown): string {
  const text = JSON.stringify(sanitizePayload(value), null, 2);
  if (Buffer.byteLength(text, "utf8") <= MAX_TOOL_TEXT_BYTES) {
    return text;
  }
  return JSON.stringify(
    {
      truncated: true,
      reason: "sanitized response exceeded model-visible output limit",
      byteLength: Buffer.byteLength(text, "utf8"),
    },
    null,
    2,
  );
}

async function fetchOrisJson(
  config: ResolvedPluginConfig,
  pathname: string,
): Promise<unknown> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.requestTimeoutMs);
  try {
    const target = new URL(pathname, `${config.baseUrl}/`);
    if (target.origin !== config.baseUrl) {
      throw new Error("refusing cross-origin ORIS request");
    }
    const response = await fetch(target, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    const text = await response.text();
    if (Buffer.byteLength(text, "utf8") > MAX_RESPONSE_BYTES) {
      throw new Error("ORIS response exceeded maximum size");
    }
    let payload: unknown;
    try {
      payload = text ? JSON.parse(text) : {};
    } catch {
      throw new Error(`ORIS returned non-JSON response with status ${response.status}`);
    }
    if (!response.ok) {
      const safe = boundedToolText(payload);
      throw new Error(`ORIS request failed with status ${response.status}: ${safe}`);
    }
    return sanitizePayload(payload);
  } finally {
    clearTimeout(timeout);
  }
}

function toolResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: boundedToolText(value) }],
    details: {
      source: "oris-dev-employee",
      readOnly: true,
      sanitized: true,
    },
  };
}

export function createTelemetryRecord(
  eventName: TelemetryRecord["event"],
  eventValue: unknown,
): TelemetryRecord {
  const event = asObject(eventValue);
  const context = asObject(event.context);
  const errorValue = event.error;
  const record: TelemetryRecord = {
    timestamp: new Date().toISOString(),
    event: eventName,
  };
  const durationMs = numberOrUndefined(event.durationMs);
  const outcome = stringOrUndefined(event.outcome);
  const success = booleanOrUndefined(event.success);
  const provider = stringOrUndefined(event.provider);
  const model = stringOrUndefined(event.model);
  const toolName = stringOrUndefined(event.toolName);
  const runHash = hashIdentifier(event.runId ?? context.runId);
  const callHash = hashIdentifier(event.callId ?? event.toolCallId);
  const sessionHash = hashIdentifier(event.sessionKey ?? context.sessionKey ?? event.sessionId);
  const error =
    typeof errorValue === "boolean"
      ? errorValue
      : errorValue === undefined || errorValue === null
        ? undefined
        : true;
  if (durationMs !== undefined) record.durationMs = durationMs;
  if (outcome !== undefined) record.outcome = outcome;
  if (success !== undefined) record.success = success;
  if (error !== undefined) record.error = error;
  if (provider !== undefined) record.provider = provider;
  if (model !== undefined) record.model = model;
  if (toolName !== undefined) record.toolName = toolName;
  if (runHash !== undefined) record.runHash = runHash;
  if (callHash !== undefined) record.callHash = callHash;
  if (sessionHash !== undefined) record.sessionHash = sessionHash;
  return record;
}

class TelemetryWriter {
  private pending: Promise<void> = Promise.resolve();

  constructor(private readonly config: ResolvedPluginConfig) {}

  write(eventName: TelemetryRecord["event"], eventValue: unknown): Promise<void> {
    if (!this.config.telemetryEnabled) {
      return Promise.resolve();
    }
    this.pending = this.pending
      .then(() => this.append(createTelemetryRecord(eventName, eventValue)))
      .catch(() => undefined);
    return this.pending;
  }

  private async append(record: TelemetryRecord): Promise<void> {
    const target = this.config.telemetryPath;
    await mkdir(dirname(target), { recursive: true, mode: 0o700 });
    try {
      const current = await stat(target);
      if (current.size >= this.config.telemetryMaxBytes) {
        const rotated = `${target}.1`;
        await unlink(rotated).catch(() => undefined);
        await rename(target, rotated);
      }
    } catch {
      // A missing telemetry file is expected on first write.
    }
    await appendFile(target, `${JSON.stringify(record)}\n`, {
      encoding: "utf8",
      mode: 0o600,
    });
  }
}

export default definePluginEntry({
  id: "oris-dev-employee",
  name: "ORIS Dev Employee",
  description: "Read-only ORIS task status tools with latency telemetry.",
  configSchema,
  register(api) {
    const config = resolvePluginConfig(api.pluginConfig);
    const telemetry = new TelemetryWriter(config);

    api.registerTool(
      {
        name: "oris_queue_status",
        label: "ORIS Queue Status",
        description:
          "Read the current ORIS Dev Employee queue. This tool is read-only and does not submit or modify tasks.",
        parameters: Type.Object({}, { additionalProperties: false }),
        async execute() {
          return toolResult(await fetchOrisJson(config, "/queue"));
        },
      },
      { optional: true },
    );

    api.registerTool(
      {
        name: "oris_task_status",
        label: "ORIS Task Status",
        description:
          "Read status and sanitized evidence metadata for one known ORIS Dev Employee task id.",
        parameters: Type.Object(
          {
            task_id: Type.String({
              minLength: 3,
              maxLength: 120,
              pattern: "^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,120}$",
            }),
          },
          { additionalProperties: false },
        ),
        async execute(_toolCallId, params) {
          const taskIdValue = asObject(params).task_id;
          const taskId = typeof taskIdValue === "string" ? taskIdValue : "";
          if (!TASK_ID_RE.test(taskId)) {
            throw new Error("invalid ORIS task id");
          }
          return toolResult(
            await fetchOrisJson(config, `/task/${encodeURIComponent(taskId)}`),
          );
        },
      },
      { optional: true },
    );

    api.registerTool(
      {
        name: "oris_latest_task_status",
        label: "ORIS Latest Task Status",
        description:
          "Read the latest sanitized ORIS Dev Employee progress snapshot. This tool is read-only.",
        parameters: Type.Object({}, { additionalProperties: false }),
        async execute() {
          return toolResult(await fetchOrisJson(config, "/latest"));
        },
      },
      { optional: true },
    );

    api.on(
      "model_call_ended",
      async (event) => {
        await telemetry.write("model_call_ended", event);
      },
      { timeoutMs: 5_000 },
    );

    api.on(
      "after_tool_call",
      async (event) => {
        await telemetry.write("after_tool_call", event);
      },
      { timeoutMs: 5_000 },
    );

    api.on(
      "agent_end",
      async (event) => {
        await telemetry.write("agent_end", event);
      },
      { timeoutMs: 5_000 },
    );
  },
});
