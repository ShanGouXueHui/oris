import type { ResolvedPluginConfig } from "./config.js";
import { boundedToolText, sanitizePayload } from "./sanitize.js";

const MAX_RESPONSE_BYTES = 1_000_000;

export async function fetchOrisJson(
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

export function toolResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: boundedToolText(value) }],
    details: {
      source: "oris-dev-employee",
      readOnly: true,
      sanitized: true,
    },
  };
}
