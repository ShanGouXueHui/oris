export type JsonObject = Record<string, unknown>;

export const MAX_TOOL_TEXT_BYTES = 32_000;

const FORBIDDEN_KEY_RE =
  /(token|password|secret|authorization|credential|api.?key|cookie|header|prompt|content|environment|env|workdir|codex|private|absolute.?path|^path$)/i;
const ABSOLUTE_PATH_RE = /\/(?:home|root|etc|var|opt|srv|tmp)\/[A-Za-z0-9._~!$&'()+,;=:@%\/-]+/g;
const BEARER_RE = /Bearer\s+[A-Za-z0-9._~+\/-]+/gi;

export function asObject(value: unknown): JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonObject)
    : {};
}

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

export function boundedToolText(value: unknown): string {
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
