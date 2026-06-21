import { createHash } from "node:crypto";
import { appendFile, mkdir, rename, stat, unlink } from "node:fs/promises";
import { dirname } from "node:path";

import type { ResolvedPluginConfig } from "./config.js";
import { asObject } from "./sanitize.js";

export type TelemetryRecord = {
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

export class TelemetryWriter {
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
