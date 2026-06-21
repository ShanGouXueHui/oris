import { homedir } from "node:os";
import { resolve } from "node:path";

import { buildJsonPluginConfigSchema } from "openclaw/plugin-sdk/plugin-entry";

const DEFAULT_HOST = ["127", "0", "0", "1"].join(".");
const DEFAULT_PORT = 18_891;
const DEFAULT_TIMEOUT_MS = 5_000;
const DEFAULT_TELEMETRY_PATH = "~/.local/state/oris/openclaw-plugin/latency.jsonl";
const DEFAULT_TELEMETRY_MAX_BYTES = 5_242_880;

export const DEFAULT_BASE_URL = `http://${DEFAULT_HOST}:${DEFAULT_PORT}`;

export type ResolvedPluginConfig = {
  baseUrl: string;
  requestTimeoutMs: number;
  telemetryEnabled: boolean;
  telemetryPath: string;
  telemetryMaxBytes: number;
};

type JsonObject = Record<string, unknown>;

function asObject(value: unknown): JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonObject)
    : {};
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
  if (!new Set([DEFAULT_HOST, "localhost", "::1"]).has(host)) {
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

export const configSchema = buildJsonPluginConfigSchema(
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
