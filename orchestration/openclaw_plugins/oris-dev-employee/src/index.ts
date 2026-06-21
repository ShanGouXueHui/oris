import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

import { configSchema, resolvePluginConfig } from "./config.js";
import { registerReadOnlyTools } from "./tools.js";
import { TelemetryWriter } from "./telemetry.js";

export { DEFAULT_BASE_URL, resolvePluginConfig } from "./config.js";
export { sanitizePayload } from "./sanitize.js";
export { createTelemetryRecord } from "./telemetry.js";

export default definePluginEntry({
  id: "oris-dev-employee",
  name: "ORIS Dev Employee",
  description: "Read-only ORIS task status tools with latency telemetry.",
  configSchema,
  register(api) {
    const config = resolvePluginConfig(api.pluginConfig);
    const telemetry = new TelemetryWriter(config);
    registerReadOnlyTools(api, config);

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
