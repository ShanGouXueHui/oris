import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import plugin from "./index.js";

type RegisteredTool = {
  name?: unknown;
  label?: unknown;
  description?: unknown;
  parameters?: unknown;
  execute?: unknown;
};

type ToolRegistration = {
  tool: RegisteredTool;
  optional: boolean;
};

type HookRegistration = {
  name: string;
  handler: unknown;
  timeoutMs?: number;
};

const EXPECTED_TOOLS = [
  "oris_queue_status",
  "oris_task_status",
  "oris_latest_task_status",
] as const;

const EXPECTED_HOOKS = [
  "model_call_ended",
  "after_tool_call",
  "agent_end",
] as const;

function readJson(path: string): Record<string, unknown> {
  return JSON.parse(readFileSync(path, "utf8")) as Record<string, unknown>;
}

function asRecord(value: unknown): Record<string, unknown> {
  assert.ok(value !== null && typeof value === "object" && !Array.isArray(value));
  return value as Record<string, unknown>;
}

assert.equal(plugin.id, "oris-dev-employee");
assert.equal(typeof plugin.register, "function");
assert.ok(plugin.configSchema);

const configResult = plugin.configSchema?.safeParse({});
assert.equal(configResult?.success, true, "default plugin configuration must validate");

const tools: ToolRegistration[] = [];
const hooks: HookRegistration[] = [];

const mockApi = {
  pluginConfig: {},
  registerTool(toolOrFactory: unknown, options?: { optional?: boolean }) {
    assert.equal(typeof toolOrFactory, "object", "v0.1 tools must register as concrete tools");
    tools.push({
      tool: toolOrFactory as RegisteredTool,
      optional: options?.optional === true,
    });
  },
  on(name: string, handler: unknown, options?: { timeoutMs?: number }) {
    hooks.push({
      name,
      handler,
      ...(typeof options?.timeoutMs === "number" ? { timeoutMs: options.timeoutMs } : {}),
    });
  },
};

await plugin.register(mockApi as never);

assert.deepEqual(
  tools.map(({ tool }) => tool.name),
  EXPECTED_TOOLS,
  "runtime tool registration must match the approved v0.1 contract",
);

for (const registration of tools) {
  const { tool, optional } = registration;
  assert.equal(optional, true, `${String(tool.name)} must remain optional`);
  assert.equal(typeof tool.name, "string");
  assert.equal(typeof tool.label, "string");
  assert.ok((tool.label as string).trim().length > 0);
  assert.equal(typeof tool.description, "string");
  assert.ok(tool.parameters);
  assert.equal(typeof tool.execute, "function");
}

assert.deepEqual(
  hooks.map(({ name }) => name),
  EXPECTED_HOOKS,
  "runtime hook registration must match the approved telemetry contract",
);

for (const hook of hooks) {
  assert.equal(typeof hook.handler, "function");
  assert.equal(hook.timeoutMs, 5_000);
}

const manifest = readJson("openclaw.plugin.json");
const packageManifest = readJson("package.json");
const manifestContracts = asRecord(manifest.contracts);
const toolMetadata = asRecord(manifest.toolMetadata);
const openclawPackage = asRecord(packageManifest.openclaw);

assert.equal(manifest.id, plugin.id);
assert.deepEqual(manifestContracts.tools, EXPECTED_TOOLS);
assert.deepEqual(openclawPackage.extensions, ["./dist/index.js"]);
assert.ok(manifest.configSchema && typeof manifest.configSchema === "object");

for (const toolName of EXPECTED_TOOLS) {
  const metadata = asRecord(toolMetadata[toolName]);
  assert.equal(metadata.optional, true, `${toolName} manifest metadata must remain optional`);
}

const forbiddenWriteTools = new Set([
  "oris_submit_task",
  "oris_cancel_task",
  "oris_retry_task",
]);
for (const { tool } of tools) {
  assert.equal(forbiddenWriteTools.has(String(tool.name)), false);
}

console.log(
  JSON.stringify({
    result: "PASS",
    validationMode: "mixed_plugin_runtime_contract",
    pluginId: plugin.id,
    tools: EXPECTED_TOOLS,
    hooks: EXPECTED_HOOKS,
    optionalTools: tools.every(({ optional }) => optional),
    sideEffectToolsPresent: false,
  }),
);
