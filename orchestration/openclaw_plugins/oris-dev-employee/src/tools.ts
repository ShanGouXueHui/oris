import { Type } from "typebox";

import type { ResolvedPluginConfig } from "./config.js";
import { fetchOrisJson, toolResult } from "./client.js";
import { asObject } from "./sanitize.js";

const TASK_ID_RE = /^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,120}$/;

type ToolApi = {
  registerTool: (tool: unknown, options?: unknown) => void;
};

export function registerReadOnlyTools(api: ToolApi, config: ResolvedPluginConfig): void {
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
      async execute(_toolCallId: unknown, params: unknown) {
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
}
