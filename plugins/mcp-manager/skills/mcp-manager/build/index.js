#!/usr/bin/env node

// src/index.ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { spawn } from "child_process";
import { readFileSync as readFileSync4, writeFileSync as writeFileSync3, existsSync as existsSync6, appendFileSync } from "fs";
import { join as join7, dirname as dirname2 } from "path";
import { parse as parseYaml2, stringify as stringifyYaml2 } from "yaml";
import { fileURLToPath as fileURLToPath2 } from "url";
import { createInterface } from "readline";

// src/utils.ts
import { join } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";
var __filename = fileURLToPath(import.meta.url);
var __dirname = dirname(__filename);
var BASE_DIR = join(__dirname, "..");
var MCP_ROOT = join(BASE_DIR, "..");
function sanitizeLog(text) {
  if (!text) return text;
  return text.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, "[IP_REDACTED]").replace(/ghp_[A-Za-z0-9]{36,}/g, "[GH_TOKEN]").replace(/github_pat_[A-Za-z0-9_]{22,}/g, "[GH_PAT]").replace(/sk-[A-Za-z0-9]{32,}/g, "[API_KEY]").replace(/sk-ant-[A-Za-z0-9\-]{32,}/g, "[ANTHROPIC_KEY]").replace(/AKIA[A-Z0-9]{16}/g, "[AWS_ACCESS_KEY]").replace(/[A-Za-z0-9/+=]{40}(?=\s|$|")/g, "[AWS_SECRET_KEY]").replace(/Bearer\s+[A-Za-z0-9\-_.~+/]+=*/gi, "Bearer [REDACTED]").replace(/password[=:]\s*["']?[^\s"']+["']?/gi, "password=[REDACTED]").replace(/token[=:]\s*["']?[^\s"']+["']?/gi, "token=[REDACTED]").replace(/secret[=:]\s*["']?[^\s"']+["']?/gi, "secret=[REDACTED]").replace(/api[_-]?key[=:]\s*["']?[^\s"']+["']?/gi, "api_key=[REDACTED]").replace(/[A-Za-z0-9]{24,}@[A-Za-z0-9\-]+\.atlassian\.net/g, "[ATLASSIAN_TOKEN]").replace(/eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+/g, "[JWT_TOKEN]");
}

// src/hooks.ts
import { readFileSync, existsSync } from "fs";
import { join as join2 } from "path";
import { parse as parseYaml } from "yaml";
var HOOKS = {};
var HOOKS_DEFAULTS = { enabled: true, async: true, timeout: 5e3 };
function loadHooks(basePath) {
  const hooksFile = join2(basePath, "hooks.yaml");
  if (!existsSync(hooksFile)) {
    return 0;
  }
  try {
    const content = readFileSync(hooksFile, "utf-8");
    const data = parseYaml(content);
    HOOKS = data.hooks || {};
    if (data.defaults) {
      HOOKS_DEFAULTS = { ...HOOKS_DEFAULTS, ...data.defaults };
    }
    return Object.keys(HOOKS).length;
  } catch (e) {
    console.error(`Failed to load hooks: ${e}`);
    return 0;
  }
}
function matchesPattern(toolName, pattern) {
  if (pattern === "*") return true;
  if (pattern.endsWith("*")) {
    const prefix = pattern.slice(0, -1);
    return toolName.startsWith(prefix);
  }
  return toolName === pattern;
}
function findMatchingHooks(toolName) {
  const matches = [];
  for (const [pattern, config] of Object.entries(HOOKS)) {
    if (matchesPattern(toolName, pattern)) {
      matches.push([pattern, config]);
    }
  }
  return matches;
}
function extractValue(spec, args, result, serverName, toolName) {
  if (spec.startsWith("args.")) {
    const field = spec.slice(5);
    return args[field]?.toString() || null;
  }
  if (spec.startsWith("regex:")) {
    const pattern = spec.slice(6);
    try {
      const match = result.match(new RegExp(pattern));
      return match ? match[1] : null;
    } catch {
      return null;
    }
  }
  if (spec.startsWith("literal:")) {
    let value = spec.slice(8);
    value = value.replace("${server}", serverName);
    value = value.replace("${tool}", toolName);
    return value;
  }
  if (spec.startsWith("result_summary:")) {
    const length = parseInt(spec.slice(15)) || 100;
    return result.slice(0, length).replace(/\n/g, " ");
  }
  if (spec === "result") {
    return result;
  }
  return null;
}
function extractHookArgs(hook, args, result, serverName, toolName) {
  if (hook.result_contains && !result.includes(hook.result_contains)) {
    return null;
  }
  if (hook.result_not_contains && result.includes(hook.result_not_contains)) {
    return null;
  }
  const extracted = {};
  for (const [key, spec] of Object.entries(hook.extract)) {
    const value = extractValue(spec, args, result, serverName, toolName);
    if (value !== null) {
      extracted[key] = value;
    }
  }
  if (Object.keys(extracted).length === 0) {
    return null;
  }
  return extracted;
}
async function executeHooks(toolName, args, result, serverName, callServerTool2, RUNNING2, SERVERS2, log2) {
  if (!HOOKS_DEFAULTS.enabled) return;
  const matches = findMatchingHooks(toolName);
  if (matches.length === 0) return;
  for (const [pattern, hook] of matches) {
    if (!(hook.target_server in RUNNING2)) {
      log2(`HOOK ${pattern} -> ${hook.target_server} not running, skipping`);
      continue;
    }
    const hookArgs = extractHookArgs(hook, args, result, serverName, toolName);
    if (!hookArgs) {
      continue;
    }
    log2(`HOOK ${pattern} -> ${hook.target_server}.${hook.target_tool}`);
    const executeHook = async () => {
      try {
        const timeout = HOOKS_DEFAULTS.timeout;
        await callServerTool2(timeout, RUNNING2[hook.target_server], hook.target_tool, hookArgs);
        log2(`HOOK ${pattern} -> OK`);
      } catch (e) {
        log2(`HOOK ${pattern} -> ERROR: ${e.message}`);
      }
    };
    if (HOOKS_DEFAULTS.async) {
      executeHook();
    } else {
      await executeHook();
    }
  }
}

// src/operations/query/list-servers.ts
import { readdirSync, existsSync as existsSync2 } from "fs";
import { join as join3 } from "path";
async function listServers(ctx) {
  const cache = ctx.loadCapabilitiesCache();
  const lines = ["# MCP Servers", ""];
  if (ctx.projectName && ctx.allowedServers) {
    lines.push(`Project: ${ctx.projectName}`);
    lines.push(`Allowed: ${ctx.allowedServers.join(", ")}`);
    lines.push("");
  }
  const running = [];
  const stopped = [];
  const disabled = [];
  for (const name of Object.keys(ctx.SERVERS).sort()) {
    if (!ctx.isServerAllowed(name)) continue;
    const config = ctx.SERVERS[name];
    if (name in ctx.RUNNING) {
      running.push(name);
    } else if (config.enabled === false) {
      disabled.push(name);
    } else {
      stopped.push(name);
    }
  }
  if (running.length > 0) {
    lines.push("## RUNNING");
    for (const name of running) {
      const config = ctx.SERVERS[name];
      const cached = cache[name];
      const tools2 = ctx.TOOLS[name] || cached?.tools || [];
      const toolCount = tools2.length;
      lines.push(`  ${name} (${toolCount} tools) - ${config.description || ""}`);
    }
    lines.push("");
  }
  if (stopped.length > 0) {
    lines.push("## STOPPED");
    for (const name of stopped) {
      const config = ctx.SERVERS[name];
      lines.push(`  ${name} - ${config.description || ""}`);
    }
    lines.push("");
  }
  if (disabled.length > 0) {
    lines.push("## DISABLED");
    for (const name of disabled) {
      const config = ctx.SERVERS[name];
      lines.push(`  ${name} - ${config.description || ""}`);
    }
    lines.push("");
  }
  const totalAllowed = running.length + stopped.length + disabled.length;
  const totalAll = Object.keys(ctx.SERVERS).length;
  if (ctx.allowedServers) {
    lines.push(`Showing: ${totalAllowed}/${totalAll} servers | ${running.length} running | ${stopped.length} stopped | ${disabled.length} disabled`);
  } else {
    lines.push(`Total: ${totalAll} servers | ${running.length} running | ${stopped.length} stopped | ${disabled.length} disabled`);
  }
  if (!ctx.allowedServers) {
    const MCP_ROOT2 = join3(ctx.BASE_DIR, "..");
    const folders = existsSync2(MCP_ROOT2) ? readdirSync(MCP_ROOT2).filter(
      (f) => f.startsWith("mcp-") && f !== "mcp-manager" && existsSync2(join3(MCP_ROOT2, f, "metadata.yaml"))
    ) : [];
    const registeredNames = Object.keys(ctx.SERVERS).map((n) => `mcp-${n}`);
    const unregistered = folders.filter((f) => !registeredNames.includes(f) && !(f in ctx.SERVERS));
    if (unregistered.length > 0) {
      lines.push("");
      lines.push("## UNREGISTERED (run discover to add)");
      for (const folder of unregistered) {
        const meta = ctx.readServerMetadata(folder);
        if (meta) {
          lines.push(`  ${folder} - ${meta.description || "no description"}`);
        }
      }
    }
  }
  return { content: [{ type: "text", text: lines.join("\n") }] };
}

// src/operations/query/search.ts
async function search(ctx, params) {
  const query = params.query;
  if (!query) {
    return { content: [{ type: "text", text: "Error: query parameter required for search" }] };
  }
  const searchTerm = query.toLowerCase();
  const shouldAutoStart = params.auto_start === true;
  const cache = ctx.loadCapabilitiesCache();
  ctx.log(`SEARCH query="${searchTerm}" auto_start=${shouldAutoStart}`);
  const matches = [];
  for (const [serverName, config] of Object.entries(ctx.SERVERS)) {
    if (config.enabled === false) continue;
    const serverInfo = cache[serverName];
    const serverDesc = config.description || serverInfo?.description || "";
    const isRunning = serverName in ctx.RUNNING;
    const serverNameMatch = serverName.toLowerCase().includes(searchTerm);
    const serverDescMatch = serverDesc.toLowerCase().includes(searchTerm);
    const tagsMatch = (config.tags || []).some((t) => t.toLowerCase().includes(searchTerm));
    if (serverNameMatch || serverDescMatch || tagsMatch) {
      matches.push({
        type: "server",
        server: serverName,
        serverDescription: serverDesc,
        running: isRunning
      });
    }
    const tools2 = serverInfo?.tools || [];
    for (const tool of tools2) {
      const nameMatch = tool.name.toLowerCase().includes(searchTerm);
      const descMatch = (tool.description || "").toLowerCase().includes(searchTerm);
      if (nameMatch || descMatch) {
        matches.push({
          type: "tool",
          server: serverName,
          serverDescription: serverDesc,
          tool: tool.name,
          toolDescription: (tool.description || "").slice(0, 80),
          running: isRunning
        });
      }
    }
  }
  ctx.log(`SEARCH found ${matches.length} matches`);
  if (matches.length === 0) {
    return { content: [{ type: "text", text: `No matches for "${query}"` }] };
  }
  const stoppedServers = [...new Set(matches.filter((m) => !m.running).map((m) => m.server))];
  const startedServers = [];
  if (shouldAutoStart && stoppedServers.length > 0) {
    for (const serverName of stoppedServers) {
      ctx.log(`SEARCH auto-starting ${serverName}...`);
      const [success, msg] = await ctx.startServer(serverName);
      if (success) {
        startedServers.push(serverName);
        matches.forEach((m) => {
          if (m.server === serverName) m.running = true;
        });
      } else {
        ctx.log(`SEARCH failed to start ${serverName}: ${msg}`);
      }
    }
  }
  const lines = [`# Search: "${query}"`, `Found ${matches.length} matches:`, ""];
  if (startedServers.length > 0) {
    lines.push(`Auto-started: ${startedServers.join(", ")}`, "");
  }
  const byServer = {};
  for (const m of matches) {
    if (!byServer[m.server]) byServer[m.server] = [];
    byServer[m.server].push(m);
  }
  for (const [serverName, serverMatches] of Object.entries(byServer)) {
    const status2 = serverMatches[0].running ? "RUNNING" : "STOPPED";
    const desc = serverMatches[0].serverDescription;
    lines.push(`## ${serverName} [${status2}]`);
    if (desc) lines.push(`   ${desc}`);
    const toolMatches = serverMatches.filter((m) => m.type === "tool");
    if (toolMatches.length > 0) {
      lines.push("   Tools:");
      for (const t of toolMatches) {
        lines.push(`     - ${t.tool}: ${t.toolDescription}`);
      }
    }
    lines.push("");
  }
  return { content: [{ type: "text", text: lines.join("\n") }] };
}

// src/operations/query/details.ts
async function details(ctx, params) {
  const serverName = params.server;
  if (!serverName) {
    return { content: [{ type: "text", text: "Error: server parameter required for details" }] };
  }
  const config = ctx.SERVERS[serverName];
  if (!config) {
    return { content: [{ type: "text", text: `Unknown server: ${serverName}` }] };
  }
  const cache = ctx.loadCapabilitiesCache();
  const cached = cache[serverName];
  const isRunning = serverName in ctx.RUNNING;
  const running = isRunning ? ctx.RUNNING[serverName] : null;
  const lines = [`# ${serverName}`, ""];
  let status2 = "STOPPED";
  if (isRunning) status2 = "RUNNING";
  else if (config.enabled === false) status2 = "DISABLED";
  lines.push(`Status: ${status2}`);
  lines.push(`Description: ${config.description || "(none)"}`);
  lines.push("");
  lines.push("## Configuration");
  if (config.url) {
    lines.push(`  Transport: HTTP`);
    lines.push(`  URL: ${config.url}`);
  } else {
    lines.push(`  Transport: stdio`);
    lines.push(`  Command: ${config.command || "(none)"}`);
    if (config.args && config.args.length > 0) {
      lines.push(`  Args: ${config.args.join(" ")}`);
    }
  }
  if (config.tags && config.tags.length > 0) {
    lines.push(`  Tags: ${config.tags.join(", ")}`);
  }
  lines.push(`  Auto-start: ${config.auto_start ? "yes" : "no"}`);
  lines.push(`  Timeout: ${config.timeout || 6e4}ms`);
  lines.push(`  Idle timeout: ${config.idle_timeout || 3e5}ms`);
  lines.push("");
  if (running) {
    lines.push("## Runtime");
    lines.push(`  Started: ${running.startedAt}`);
    const idleSeconds = Math.round((Date.now() - running.lastActivity) / 1e3);
    lines.push(`  Idle: ${idleSeconds}s`);
    if (running.process) {
      lines.push(`  PID: ${running.process.pid}`);
    }
    if (running.metadata?.cdpPort) {
      lines.push(`  CDP Port: ${running.metadata.cdpPort}`);
    }
    lines.push("");
  }
  const tools2 = ctx.TOOLS[serverName] || cached?.tools || [];
  lines.push(`## Tools (${tools2.length})`);
  if (tools2.length === 0) {
    lines.push("  (no tools cached - start server to discover)");
  } else {
    for (const tool of tools2) {
      const desc = typeof tool.description === "string" ? tool.description.slice(0, 60) : "";
      lines.push(`  - ${tool.name}: ${desc}`);
    }
  }
  return { content: [{ type: "text", text: lines.join("\n") }] };
}

// src/operations/query/tools.ts
async function tools(ctx, params) {
  const serverName = params.server;
  if (serverName) {
    if (!(serverName in ctx.RUNNING)) {
      return {
        content: [{
          type: "text",
          text: `Server not running: ${serverName}. Start it first with mcpm(operation="start", server="${serverName}")`
        }]
      };
    }
    const serverTools = ctx.TOOLS[serverName] || [];
    const lines2 = [`# ${serverName} Tools (${serverTools.length})`, ""];
    for (const tool of serverTools) {
      const desc = (tool.description || "").slice(0, 80);
      lines2.push(`  - ${tool.name}`);
      if (desc) lines2.push(`    ${desc}`);
    }
    if (serverTools.length === 0) {
      lines2.push("  (no tools)");
    }
    return { content: [{ type: "text", text: lines2.join("\n") }] };
  }
  const lines = ["# Available Tools", ""];
  const runningServers = Object.keys(ctx.RUNNING).sort();
  if (runningServers.length === 0) {
    lines.push('No servers running. Use mcpm(operation="start", server="...") to start a server.');
    return { content: [{ type: "text", text: lines.join("\n") }] };
  }
  for (const srv of runningServers) {
    const serverTools = ctx.TOOLS[srv] || [];
    lines.push(`## ${srv} (${serverTools.length} tools)`);
    for (const tool of serverTools) {
      const desc = (tool.description || "").slice(0, 50);
      lines.push(`  - ${tool.name}: ${desc}`);
    }
    lines.push("");
  }
  return { content: [{ type: "text", text: lines.join("\n") }] };
}

// src/operations/query/status.ts
import { execSync } from "child_process";
var DEFAULT_IDLE_TIMEOUT = 3e5;
function getProcessMemoryMB(pid) {
  try {
    if (process.platform === "win32") {
      const output = execSync(
        `wmic process where ProcessId=${pid} get WorkingSetSize 2>nul`,
        { encoding: "utf-8", timeout: 5e3 }
      ).trim();
      const match = output.match(/\d+/);
      if (!match) return null;
      return Math.round(parseInt(match[0], 10) / 1024 / 1024);
    } else {
      const output = execSync(`ps -o rss= -p ${pid}`, {
        encoding: "utf-8",
        timeout: 5e3
      }).trim();
      return Math.round(parseInt(output, 10) / 1024);
    }
  } catch {
    return null;
  }
}
function formatBytes(mb) {
  if (mb === null) return "?";
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)}GB`;
  return `${mb}MB`;
}
async function status(ctx) {
  const lines = ["# MCP Manager Status", ""];
  lines.push(`Registry: ${ctx.SERVERS_FILE}`);
  lines.push(`Total servers: ${Object.keys(ctx.SERVERS).length}`);
  lines.push(`Running: ${Object.keys(ctx.RUNNING).length}`);
  lines.push(`Total tools: ${Object.values(ctx.TOOLS).flat().length}`);
  lines.push("");
  const selfMem = Math.round(process.memoryUsage().heapUsed / 1024 / 1024);
  let totalMem = selfMem;
  lines.push("## Memory");
  lines.push(`  mcp-manager: ${formatBytes(selfMem)}`);
  if (Object.keys(ctx.RUNNING).length > 0) {
    lines.push("");
    lines.push("## Running Servers");
    for (const [name, info] of Object.entries(ctx.RUNNING)) {
      const idleSeconds = Math.round((Date.now() - info.lastActivity) / 1e3);
      const idleTimeout = ctx.SERVERS[name]?.idle_timeout || DEFAULT_IDLE_TIMEOUT;
      const timeUntilStop = Math.round((idleTimeout - (Date.now() - info.lastActivity)) / 1e3);
      let memStr = "remote";
      if (info.process?.pid) {
        const mem = getProcessMemoryMB(info.process.pid);
        if (mem !== null) {
          totalMem += mem;
          memStr = formatBytes(mem);
        }
      }
      lines.push(`  ${name}`);
      lines.push(`    Tools: ${info.toolsCount} | RAM: ${memStr}`);
      lines.push(`    Idle: ${idleSeconds}s (auto-stop in ${timeUntilStop > 0 ? timeUntilStop + "s" : "imminent"})`);
      if (info.url) {
        lines.push(`    URL: ${info.url}`);
      } else if (info.process) {
        lines.push(`    PID: ${info.process.pid}`);
      }
    }
  }
  lines.push("");
  lines.push(`Total RAM: ${formatBytes(totalMem)}`);
  return { content: [{ type: "text", text: lines.join("\n") }] };
}

// src/operations/query/help.ts
async function help() {
  const text = `# mcpm - MCP Server Manager

## Query Operations (read-only)
  list_servers   List all servers with status
  search         Search servers, tools, descriptions
                 params: query, auto_start?
  details        Full info on one server
                 params: server
  tools          List tools for a server (or all running)
                 params: server?
  status         System health, memory, diagnostics
  help           Show this help

## Call Operation (proxy to backend)
  call           Execute tool on backend server
                 params: server, tool, arguments?

## Admin Operations (modify state)
  start          Start a server
                 params: server
  stop           Stop a server
                 params: server
  restart        Restart a server
                 params: server
  enable         Enable a server
                 params: server, enabled
  add            Register new server
                 params: server, command, args?, description?, env?, tags?, auto_start?
  remove         Unregister a server
                 params: server
  reload         Reload servers.yaml config
  discover       Scan mcp/ folder for new servers
  usage          Show which projects use which servers
  ram            Detailed RAM usage by server

## Examples
  mcpm(operation="list_servers")
  mcpm(operation="search", query="wiki")
  mcpm(operation="details", server="v1-lite")
  mcpm(operation="start", server="wiki-lite")
  mcpm(operation="call", server="wiki-lite", tool="wiki_search", arguments={"query": "API"})
`;
  return { content: [{ type: "text", text }] };
}

// src/binary-filter.ts
import { writeFileSync, mkdirSync, existsSync as existsSync3 } from "fs";
import { join as join4 } from "path";
import { tmpdir } from "os";
var BINARY_TEMP_DIR = process.env.SCREENSHOT_DIR || join4(tmpdir(), "mcp-manager-binary");
if (!existsSync3(BINARY_TEMP_DIR)) {
  mkdirSync(BINARY_TEMP_DIR, { recursive: true });
}
var fileCounter = 0;
function getExtension(mimeType) {
  const mimeToExt = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "application/pdf": ".pdf",
    "application/octet-stream": ".bin"
  };
  return mimeToExt[mimeType] || ".bin";
}
function generateFilename(prefix, ext) {
  const timestamp = (/* @__PURE__ */ new Date()).toISOString().replace(/[:.]/g, "-");
  fileCounter++;
  return `${prefix}_${timestamp}_${fileCounter}${ext}`;
}
function writeBase64ToFile(data, mimeType, prefix = "image") {
  const ext = getExtension(mimeType);
  const filename = generateFilename(prefix, ext);
  const filepath = join4(BINARY_TEMP_DIR, filename);
  const buffer = Buffer.from(data, "base64");
  writeFileSync(filepath, buffer);
  return filepath;
}
function processContentItem(item, serverName) {
  if (item.type === "image" && "data" in item && typeof item.data === "string") {
    const imageItem = item;
    const filepath = writeBase64ToFile(
      imageItem.data,
      imageItem.mimeType || "image/png",
      `${serverName}_screenshot`
    );
    return {
      type: "text",
      text: `[Image saved to: ${filepath}]
(MIME: ${imageItem.mimeType || "image/png"}, Size: ${Math.round(imageItem.data.length * 0.75 / 1024)}KB)`
    };
  }
  if (item.type === "resource" && "resource" in item) {
    const resourceItem = item;
    if (resourceItem.resource.blob && typeof resourceItem.resource.blob === "string") {
      const filepath = writeBase64ToFile(
        resourceItem.resource.blob,
        resourceItem.resource.mimeType || "application/octet-stream",
        `${serverName}_resource`
      );
      return {
        type: "text",
        text: `[Resource saved to: ${filepath}]
(URI: ${resourceItem.resource.uri}, MIME: ${resourceItem.resource.mimeType || "unknown"})`
      };
    }
  }
  if (typeof item === "object" && item !== null) {
    for (const [key, value] of Object.entries(item)) {
      if (typeof value === "string" && value.length > 1e4) {
        if (/^[A-Za-z0-9+/]+=*$/.test(value.slice(0, 1e3))) {
          const filepath = writeBase64ToFile(
            value,
            "application/octet-stream",
            `${serverName}_${key}`
          );
          return {
            ...item,
            [key]: `[Binary data saved to: ${filepath}]`
          };
        }
      }
    }
  }
  return item;
}
function processBinaryContent(content, serverName) {
  if (!content || !Array.isArray(content)) {
    return content || [];
  }
  return content.map((item) => processContentItem(item, serverName));
}

// src/operations/call/call.ts
async function call(ctx, params) {
  const serverName = params.server;
  const toolName = params.tool;
  const args = params.arguments || {};
  if (!serverName) {
    return { content: [{ type: "text", text: "Error: server parameter required" }] };
  }
  if (!toolName) {
    return { content: [{ type: "text", text: "Error: tool parameter required" }] };
  }
  if (!ctx.isServerAllowed(serverName)) {
    const projectInfo = ctx.projectName ? ` (project: ${ctx.projectName})` : "";
    ctx.log(`CALL ${serverName}:${toolName} -> BLOCKED: server not in allowedServers${projectInfo}`);
    return {
      content: [{
        type: "text",
        text: `Error: Server '${serverName}' is not allowed for this project${projectInfo}. Allowed: ${ctx.allowedServers?.join(", ") || "all"}`
      }]
    };
  }
  const argsStr = JSON.stringify(args).slice(0, 200);
  if (!(serverName in ctx.RUNNING)) {
    if (serverName in ctx.SERVERS && ctx.SERVERS[serverName].enabled !== false) {
      ctx.log(`CALL ${serverName}:${toolName} -> Auto-starting server...`);
      const [success, msg] = await ctx.startServer(serverName);
      if (!success) {
        ctx.log(`CALL ${serverName}:${toolName} -> ERROR: failed to auto-start: ${msg}`);
        return { content: [{ type: "text", text: `Failed to auto-start ${serverName}: ${msg}` }] };
      }
      ctx.log(`CALL ${serverName}:${toolName} -> Server auto-started successfully`);
    } else {
      ctx.log(`CALL ${serverName}:${toolName} -> ERROR: server not found or disabled`);
      return { content: [{ type: "text", text: `Server not found or disabled: ${serverName}` }] };
    }
  }
  ctx.log(`CALL ${serverName}:${toolName} args=${argsStr}`);
  const startTime = Date.now();
  ctx.RUNNING[serverName].lastActivity = Date.now();
  const executeCall = async (attempt = 1) => {
    try {
      const reqTimeout = ctx.SERVERS[serverName]?.timeout || 6e4;
      const result = await ctx.callServerTool(reqTimeout, ctx.RUNNING[serverName], toolName, args);
      const elapsed = Date.now() - startTime;
      const rawContent = result?.content;
      const content = processBinaryContent(rawContent, serverName);
      let resultText;
      if (Array.isArray(content)) {
        const texts = content.filter((c) => c.type === "text").map((c) => c.text);
        resultText = texts.join("\n");
        const resultPreview = resultText.slice(0, 100).replace(/\n/g, " ");
        ctx.log(`CALL ${serverName}:${toolName} -> OK (${elapsed}ms) ${resultPreview}...`);
      } else {
        resultText = JSON.stringify(result, null, 2);
        ctx.log(`CALL ${serverName}:${toolName} -> OK (${elapsed}ms)`);
      }
      if (attempt === 1 && serverName === "blueprint" && resultText.includes("Extension not connected")) {
        ctx.log(`CALL ${serverName}:${toolName} -> Extension timing issue, auto-retrying...`);
        await new Promise((r) => setTimeout(r, 500));
        return executeCall(2);
      }
      executeHooks(toolName, args, resultText, serverName, ctx.callServerTool, ctx.RUNNING, ctx.SERVERS, ctx.log);
      return { content: [{ type: "text", text: resultText }] };
    } catch (e) {
      const elapsed = Date.now() - startTime;
      ctx.log(`CALL ${serverName}:${toolName} -> ERROR (${elapsed}ms): ${e.message}`);
      return { content: [{ type: "text", text: `Error: ${e.message}` }] };
    }
  };
  return executeCall();
}

// src/operations/admin/lifecycle.ts
async function start(ctx, params) {
  const serverName = params.server;
  if (!serverName) {
    return { content: [{ type: "text", text: "Error: server parameter required" }] };
  }
  ctx.log(`START ${serverName}`);
  const [success, message] = await ctx.startServer(serverName);
  ctx.log(`START ${serverName} -> ${success ? "OK" : "FAILED"}: ${message}`);
  return { content: [{ type: "text", text: message }] };
}
async function stop(ctx, params) {
  const serverName = params.server;
  if (!serverName) {
    return { content: [{ type: "text", text: "Error: server parameter required" }] };
  }
  ctx.log(`STOP ${serverName}`);
  const [success, message] = ctx.stopServer(serverName);
  ctx.log(`STOP ${serverName} -> ${success ? "OK" : "FAILED"}: ${message}`);
  return { content: [{ type: "text", text: message }] };
}
async function restart(ctx, params) {
  const serverName = params.server;
  if (!serverName) {
    return { content: [{ type: "text", text: "Error: server parameter required" }] };
  }
  ctx.log(`RESTART ${serverName}`);
  const [success, message] = await ctx.restartServer(serverName);
  ctx.log(`RESTART ${serverName} -> ${success ? "OK" : "FAILED"}: ${message}`);
  return { content: [{ type: "text", text: message }] };
}
async function enable(ctx, params) {
  const serverName = params.server;
  if (!serverName) {
    return { content: [{ type: "text", text: "Error: server parameter required" }] };
  }
  if (!(serverName in ctx.SERVERS)) {
    return { content: [{ type: "text", text: `Unknown server: ${serverName}` }] };
  }
  const enabled = params.enabled !== false;
  ctx.SERVERS[serverName].enabled = enabled;
  ctx.saveServersConfig();
  if (!enabled && serverName in ctx.RUNNING) {
    ctx.stopServer(serverName);
  }
  return { content: [{ type: "text", text: `${enabled ? "Enabled" : "Disabled"} server: ${serverName}` }] };
}

// src/operations/admin/registry.ts
import { existsSync as existsSync4, readdirSync as readdirSync2, readFileSync as readFileSync2, writeFileSync as writeFileSync2 } from "fs";
import { join as join5 } from "path";
import { stringify as stringifyYaml } from "yaml";
function updateProjectServers(action, serverName) {
  const projectPath = process.env.MCPM_PROJECT_PATH;
  if (!projectPath) return null;
  const mcpJsonPath = join5(projectPath, ".mcp.json");
  if (!existsSync4(mcpJsonPath)) return null;
  try {
    const content = readFileSync2(mcpJsonPath, "utf-8");
    const config = JSON.parse(content);
    const mcpManager = config.mcpServers?.["mcp-manager"];
    if (!mcpManager) return null;
    if (!mcpManager.servers) {
      mcpManager.servers = [];
    }
    if (action === "add") {
      if (!mcpManager.servers.includes(serverName)) {
        mcpManager.servers.push(serverName);
        mcpManager.servers.sort();
      }
    } else if (action === "remove") {
      mcpManager.servers = mcpManager.servers.filter((s) => s !== serverName);
    }
    delete mcpManager.allowedServers;
    writeFileSync2(mcpJsonPath, JSON.stringify(config, null, 2));
    return `Updated project .mcp.json`;
  } catch (e) {
    return `Warning: Could not update project .mcp.json: ${e.message}`;
  }
}
async function add(ctx, params) {
  const serverName = params.server;
  const command = params.command;
  if (!serverName) {
    return { content: [{ type: "text", text: "Error: server parameter required" }] };
  }
  if (!command) {
    return { content: [{ type: "text", text: "Error: command parameter required" }] };
  }
  if (serverName in ctx.SERVERS) {
    return { content: [{ type: "text", text: `Server already exists: ${serverName}. Use remove first.` }] };
  }
  ctx.SERVERS[serverName] = {
    name: serverName,
    command,
    args: params.args || [],
    description: params.description || "",
    env: params.env || {},
    enabled: true,
    auto_start: params.auto_start || false,
    tags: params.tags || []
  };
  ctx.saveServersConfig();
  const projectMsg = updateProjectServers("add", serverName);
  const msg = projectMsg ? `Added server: ${serverName}. ${projectMsg}` : `Added server: ${serverName}`;
  return { content: [{ type: "text", text: msg }] };
}
async function remove(ctx, params) {
  const serverName = params.server;
  if (!serverName) {
    return { content: [{ type: "text", text: "Error: server parameter required" }] };
  }
  if (!(serverName in ctx.SERVERS)) {
    return { content: [{ type: "text", text: `Unknown server: ${serverName}` }] };
  }
  if (serverName in ctx.RUNNING) {
    ctx.stopServer(serverName);
  }
  delete ctx.SERVERS[serverName];
  ctx.saveServersConfig();
  const projectMsg = updateProjectServers("remove", serverName);
  const msg = projectMsg ? `Removed server: ${serverName}. ${projectMsg}` : `Removed server: ${serverName}`;
  return { content: [{ type: "text", text: msg }] };
}
async function reload(ctx) {
  const oldCount = Object.keys(ctx.SERVERS).length;
  const oldAllowed = ctx.allowedServers ? [...ctx.allowedServers] : null;
  try {
    const count = ctx.loadServersConfig();
    ctx.reloadProjectConfig();
    const runningCount = Object.keys(ctx.RUNNING).length;
    const newAllowed = ctx.allowedServers;
    let allowedMsg = "";
    if (JSON.stringify(oldAllowed) !== JSON.stringify(newAllowed)) {
      if (newAllowed) {
        allowedMsg = " Allowed servers updated: " + newAllowed.join(", ") + ".";
      } else {
        allowedMsg = " Allowed servers filter removed (all servers accessible).";
      }
    }
    return {
      content: [{
        type: "text",
        text: `Reloaded config: ${count} servers (was ${oldCount}), ${runningCount} running.${allowedMsg} New timeout/config values will apply to next server start.`
      }]
    };
  } catch (e) {
    return { content: [{ type: "text", text: `Failed to reload: ${e.message}` }] };
  }
}
function discoverNewServers(ctx) {
  const MCP_ROOT2 = join5(ctx.BASE_DIR, "..");
  const discovered = [];
  if (!existsSync4(MCP_ROOT2)) return discovered;
  try {
    const entries = readdirSync2(MCP_ROOT2, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory() || !entry.name.startsWith("mcp-")) continue;
      if (entry.name === "mcp-manager") continue;
      const folderPath = join5(MCP_ROOT2, entry.name);
      const hasMetadata = existsSync4(join5(folderPath, "metadata.yaml"));
      const packageJsonPath = join5(folderPath, "package.json");
      const serverPyPath = join5(folderPath, "server.py");
      let type = "unknown";
      let command = "";
      let args = [];
      let description = "";
      let entryPoint = null;
      if (existsSync4(packageJsonPath)) {
        try {
          const pkg = JSON.parse(readFileSync2(packageJsonPath, "utf-8"));
          type = "node";
          description = pkg.description || "";
          if (pkg.main) {
            entryPoint = join5(folderPath, pkg.main);
            command = "node";
            args = [entryPoint];
          } else if (pkg.bin) {
            const binName = Object.keys(pkg.bin)[0];
            if (binName) {
              entryPoint = join5(folderPath, pkg.bin[binName]);
              command = "node";
              args = [entryPoint];
            }
          }
          if (entryPoint && !existsSync4(entryPoint)) {
            const cjsVariant = entryPoint.replace(/\.js$/, ".cjs");
            if (existsSync4(cjsVariant)) {
              entryPoint = cjsVariant;
              args = [entryPoint];
            } else if (pkg.scripts?.build) {
              entryPoint = null;
            }
          }
        } catch {
        }
      } else if (existsSync4(serverPyPath)) {
        type = "python";
        entryPoint = serverPyPath;
        command = "uv";
        args = ["run", "--with", "mcp", "python", serverPyPath];
        try {
          const pyContent = readFileSync2(serverPyPath, "utf-8");
          const docMatch = pyContent.match(/^"""([^"]+)"""/m) || pyContent.match(/^'''([^']+)'''/m);
          if (docMatch) {
            description = docMatch[1].trim().split("\n")[0];
          }
        } catch {
        }
      }
      discovered.push({
        name: entry.name,
        type,
        command,
        args,
        description,
        hasMetadata,
        entryPoint
      });
    }
  } catch (e) {
    ctx.log(`Error scanning MCP folders: ${e.message}`);
  }
  return discovered;
}
function createMetadataYaml(ctx, server2) {
  const MCP_ROOT2 = join5(ctx.BASE_DIR, "..");
  const metadataPath = join5(MCP_ROOT2, server2.name, "metadata.yaml");
  if (existsSync4(metadataPath)) return false;
  const metadata = {
    name: server2.name,
    description: server2.description || `${server2.name} MCP server`,
    version: "1.0.0",
    source: "cloned",
    status: server2.entryPoint ? "active" : "needs_build",
    tags: [],
    tokens: "~2000",
    maintainer: "joel",
    used_by: []
  };
  if (server2.type === "node") metadata.tags.push("node");
  if (server2.type === "python") metadata.tags.push("python");
  try {
    writeFileSync2(metadataPath, stringifyYaml(metadata));
    return true;
  } catch {
    return false;
  }
}
function registerNewServer(ctx, server2) {
  if (!server2.entryPoint || !server2.command) return false;
  const shortName = server2.name.replace(/^mcp-/, "");
  if (shortName in ctx.SERVERS || server2.name in ctx.SERVERS) return false;
  const config = {
    name: shortName,
    description: server2.description || `${server2.name} server`,
    command: server2.command,
    args: server2.args,
    enabled: true,
    auto_start: false,
    tags: [server2.type]
  };
  if (server2.type === "python") {
    config.startup_delay = 3e3;
  }
  ctx.SERVERS[shortName] = config;
  return true;
}
async function discover(ctx) {
  const discovered = discoverNewServers(ctx);
  let created = 0;
  let registered = 0;
  for (const server2 of discovered) {
    if (!server2.hasMetadata) {
      if (createMetadataYaml(ctx, server2)) {
        created++;
        ctx.log(`  Created metadata.yaml for ${server2.name}`);
      }
    }
    if (registerNewServer(ctx, server2)) {
      registered++;
      ctx.log(`  Registered ${server2.name} in servers.yaml`);
    }
  }
  if (registered > 0) {
    ctx.saveServersConfig();
  }
  const lines = ["# MCP Server Discovery", ""];
  lines.push(`Found ${discovered.length} MCP server folders:`);
  lines.push("");
  for (const srv of discovered) {
    const statusIcon = srv.entryPoint ? "[OK]" : "[NEEDS BUILD]";
    const shortName = srv.name.replace(/^mcp-/, "");
    const regStatus = shortName in ctx.SERVERS ? "registered" : "not registered";
    lines.push(`  ${srv.name} (${srv.type}) ${statusIcon}`);
    lines.push(`    Status: ${regStatus}`);
  }
  lines.push("");
  lines.push(`Created ${created} metadata.yaml files`);
  lines.push(`Registered ${registered} new servers`);
  return { content: [{ type: "text", text: lines.join("\n") }] };
}

// src/operations/admin/usage.ts
import { existsSync as existsSync5, readdirSync as readdirSync3, readFileSync as readFileSync3 } from "fs";
import { join as join6 } from "path";
import { execSync as execSync2 } from "child_process";
function scanProjectUsage(ctx) {
  const usage2 = {};
  const PROJECTS_ROOT = join6(ctx.BASE_DIR, "..", "..");
  if (!existsSync5(PROJECTS_ROOT)) {
    return usage2;
  }
  try {
    const entries = readdirSync3(PROJECTS_ROOT, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const mcpJsonPath = join6(PROJECTS_ROOT, entry.name, ".mcp.json");
      if (!existsSync5(mcpJsonPath)) continue;
      try {
        const content = readFileSync3(mcpJsonPath, "utf-8");
        const config = JSON.parse(content);
        const servers = config.mcpServers || {};
        for (const [serverKey, serverConfig] of Object.entries(servers)) {
          let mcpName = null;
          const args = serverConfig.args || [];
          for (const arg of args) {
            if (typeof arg === "string") {
              const match = arg.match(/mcp[\/\\](mcp-[^\/\\]+)/);
              if (match) {
                mcpName = match[1];
                break;
              }
            }
          }
          if (!mcpName && serverKey.startsWith("mcp-")) {
            mcpName = serverKey;
          }
          if (!mcpName) {
            const possibleName = `mcp-${serverKey}`;
            const possiblePath = join6(ctx.BASE_DIR, "..", possibleName);
            if (existsSync5(possiblePath)) {
              mcpName = possibleName;
            }
          }
          if (mcpName) {
            if (!usage2[mcpName]) {
              usage2[mcpName] = [];
            }
            if (!usage2[mcpName].includes(entry.name)) {
              usage2[mcpName].push(entry.name);
            }
          }
        }
      } catch {
      }
    }
  } catch {
  }
  return usage2;
}
async function usage(ctx) {
  const usageMap = scanProjectUsage(ctx);
  const lines = ["# MCP Server Usage", ""];
  const MCP_ROOT2 = join6(ctx.BASE_DIR, "..");
  const allServers = [];
  try {
    const entries = readdirSync3(MCP_ROOT2, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isDirectory() && entry.name.startsWith("mcp-")) {
        allServers.push(entry.name);
      }
    }
  } catch {
  }
  const used = [];
  const unused = [];
  for (const server2 of allServers.sort()) {
    const projects = usageMap[server2];
    if (projects && projects.length > 0) {
      used.push([server2, projects]);
    } else {
      unused.push(server2);
    }
  }
  if (used.length > 0) {
    lines.push("## In Use");
    for (const [server2, projects] of used) {
      lines.push(`  ${server2}`);
      for (const proj of projects.sort()) {
        lines.push(`    - ${proj}`);
      }
    }
    lines.push("");
  }
  if (unused.length > 0) {
    lines.push("## Not Used");
    for (const server2 of unused) {
      lines.push(`  ${server2}`);
    }
    lines.push("");
  }
  lines.push(`Total: ${allServers.length} servers, ${used.length} in use, ${unused.length} not used`);
  return { content: [{ type: "text", text: lines.join("\n") }] };
}
function getProcessMemoryMB2(pid) {
  try {
    if (process.platform === "win32") {
      const output = execSync2(
        `wmic process where ProcessId=${pid} get WorkingSetSize 2>nul`,
        { encoding: "utf-8", timeout: 5e3 }
      ).trim();
      const match = output.match(/\d+/);
      if (!match) return null;
      return Math.round(parseInt(match[0], 10) / 1024 / 1024);
    } else {
      const output = execSync2(`ps -o rss= -p ${pid}`, {
        encoding: "utf-8",
        timeout: 5e3
      }).trim();
      return Math.round(parseInt(output, 10) / 1024);
    }
  } catch {
    return null;
  }
}
function formatBytes2(mb) {
  if (mb === null) return "?";
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)}GB`;
  return `${mb}MB`;
}
async function ram(ctx) {
  const lines = [];
  const WIDTH = 52;
  const selfMem = Math.round(process.memoryUsage().heapUsed / 1024 / 1024);
  let totalMem = selfMem;
  const serverData = [];
  for (const name of Object.keys(ctx.RUNNING).sort()) {
    const server2 = ctx.RUNNING[name];
    const pid = server2.process?.pid;
    const mem = pid ? getProcessMemoryMB2(pid) : null;
    if (mem !== null) totalMem += mem;
    const tools2 = (ctx.TOOLS[name] || []).map((t) => t.name);
    const isHttp = !!server2.url;
    serverData.push({ name, ram: mem, tools: tools2, isHttp });
  }
  lines.push("MCP Servers");
  lines.push("");
  const mgrLabel = "mcp-manager (this)";
  const mgrMem = formatBytes2(selfMem);
  const mgrPad = WIDTH - mgrLabel.length - 4 - mgrMem.length;
  lines.push(`\u251C\u2500\u2500 ${mgrLabel}${".".repeat(Math.max(1, mgrPad))}${mgrMem}`);
  for (let i = 0; i < serverData.length; i++) {
    const srv = serverData[i];
    const isLast = i === serverData.length - 1;
    const prefix = isLast ? "\u2514\u2500\u2500 " : "\u251C\u2500\u2500 ";
    const childPrefix = isLast ? "    " : "\u2502   ";
    const transportNote = srv.isHttp ? " [HTTP]" : "";
    const serverLabel = `${srv.name}${transportNote} (${srv.tools.length} tools)`;
    const ramStr = srv.isHttp ? "remote" : formatBytes2(srv.ram);
    const padding = WIDTH - serverLabel.length - prefix.length - ramStr.length;
    lines.push(`${prefix}${serverLabel}${".".repeat(Math.max(1, padding))}${ramStr}`);
    for (let j = 0; j < srv.tools.length; j++) {
      const toolName = srv.tools[j];
      const isLastTool = j === srv.tools.length - 1;
      const toolPrefix = isLastTool ? "\u2514\u2500\u2500 " : "\u251C\u2500\u2500 ";
      lines.push(`${childPrefix}${toolPrefix}${toolName}`);
    }
  }
  if (serverData.length === 0) {
    lines.push("\u2514\u2500\u2500 (no backend servers running)");
  }
  lines.push("");
  const totalLabel = "Total RAM";
  const totalStr = formatBytes2(totalMem);
  const totalPad = WIDTH - totalLabel.length - totalStr.length;
  lines.push(`${totalLabel}${".".repeat(Math.max(1, totalPad))}${totalStr}`);
  return { content: [{ type: "text", text: lines.join("\n") }] };
}

// src/index.ts
var __filename2 = fileURLToPath2(import.meta.url);
var __dirname2 = dirname2(__filename2);
var BASE_DIR2 = join7(__dirname2, "..");
var SERVERS_FILE = join7(BASE_DIR2, "servers.yaml");
var LOG_FILE = join7(BASE_DIR2, "mcp-manager.log");
var CAPABILITIES_CACHE_FILE = join7(BASE_DIR2, "capabilities-cache.yaml");
var SERVERS = {};
var RUNNING = {};
var TOOLS = {};
var TOOL_MAP = {};
function log(message) {
  const timestamp = (/* @__PURE__ */ new Date()).toISOString();
  const sanitized = sanitizeLog(message);
  const line = `[${timestamp}] ${sanitized}`;
  console.error(line);
  try {
    appendFileSync(LOG_FILE, line + "\n");
  } catch {
  }
}
var IDLE_CHECK_INTERVAL = 6e4;
var DEFAULT_IDLE_TIMEOUT2 = 3e5;
var idleCheckTimer = null;
function checkIdleServers() {
  const now = Date.now();
  for (const [name, server2] of Object.entries(RUNNING)) {
    const config = SERVERS[name];
    const idleTimeout = config?.idle_timeout || DEFAULT_IDLE_TIMEOUT2;
    const idleTime = now - server2.lastActivity;
    if (config?.tags?.includes("no_auto_stop")) continue;
    if (idleTime < idleTimeout) continue;
    log(`IDLE: ${name} idle for ${Math.round(idleTime / 1e3)}s, stopping...`);
    const [success, msg] = stopServer(name);
    log(`IDLE: ${name} -> ${success ? "stopped" : msg}`);
  }
}
function startIdleChecker() {
  if (idleCheckTimer) return;
  idleCheckTimer = setInterval(checkIdleServers, IDLE_CHECK_INTERVAL);
  log("Idle server checker started (60s interval)");
}
function loadEnv(basePath) {
  const envFile = join7(basePath, ".env");
  if (existsSync6(envFile)) {
    const content = readFileSync4(envFile, "utf-8");
    for (const line of content.split("\n")) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith("#") && trimmed.includes("=")) {
        const [key, ...valueParts] = trimmed.split("=");
        const value = valueParts.join("=").replace(/^["']|["']$/g, "");
        process.env[key.trim()] = value;
      }
    }
  }
}
function loadServersConfig() {
  SERVERS = {};
  if (!existsSync6(SERVERS_FILE)) return 0;
  const content = readFileSync4(SERVERS_FILE, "utf-8");
  const data = parseYaml2(content);
  const defaults = data.defaults || {};
  const servers = data.servers || {};
  for (const [name, config] of Object.entries(servers)) {
    const merged = { ...defaults, ...config, name };
    if (merged.env) {
      for (const [key, value] of Object.entries(merged.env)) {
        if (typeof value === "string" && value.startsWith("${") && value.endsWith("}")) {
          const envVar = value.slice(2, -1);
          merged.env[key] = process.env[envVar] || "";
        }
      }
    }
    SERVERS[name] = merged;
  }
  return Object.keys(SERVERS).length;
}
function saveServersConfig() {
  const data = {
    servers: {},
    defaults: { timeout: 3e4, retry_count: 3, health_check_interval: 60 }
  };
  for (const [name, config] of Object.entries(SERVERS)) {
    const { name: _, timeout, retry_count, health_check_interval, ...cleanConfig } = config;
    data.servers[name] = cleanConfig;
  }
  writeFileSync3(SERVERS_FILE, stringifyYaml2(data));
}
function loadCapabilitiesCache() {
  if (!existsSync6(CAPABILITIES_CACHE_FILE)) return {};
  try {
    return parseYaml2(readFileSync4(CAPABILITIES_CACHE_FILE, "utf-8")) || {};
  } catch {
    return {};
  }
}
function updateCapabilitiesCache() {
  const cache = {};
  for (const [name, config] of Object.entries(SERVERS)) {
    const tools2 = TOOLS[name] || [];
    const metadata = readServerMetadata(`mcp-${name}`) || readServerMetadata(name);
    let toolList = tools2.map((t) => ({
      name: t.name,
      description: (t.description || "").slice(0, 100)
    }));
    if (toolList.length === 0 && metadata?.capabilities) {
      toolList = metadata.capabilities;
    }
    cache[name] = {
      description: config.description || metadata?.description || "",
      enabled: config.enabled !== false,
      running: name in RUNNING,
      tools: toolList,
      lastUpdated: (/* @__PURE__ */ new Date()).toISOString()
    };
  }
  try {
    writeFileSync3(CAPABILITIES_CACHE_FILE, stringifyYaml2(cache));
  } catch {
  }
}
function saveToolsToMetadata(serverName, tools2) {
  const MCP_ROOT2 = join7(BASE_DIR2, "..");
  let metadataPath = join7(MCP_ROOT2, `mcp-${serverName}`, "metadata.yaml");
  if (!existsSync6(dirname2(metadataPath))) {
    metadataPath = join7(MCP_ROOT2, serverName, "metadata.yaml");
  }
  if (!existsSync6(dirname2(metadataPath))) return;
  try {
    let metadata = {};
    if (existsSync6(metadataPath)) {
      metadata = parseYaml2(readFileSync4(metadataPath, "utf-8")) || {};
    }
    metadata.capabilities = tools2.map((t) => ({
      name: t.name,
      description: (t.description || "").slice(0, 100)
    }));
    metadata.last_updated = (/* @__PURE__ */ new Date()).toISOString();
    writeFileSync3(metadataPath, stringifyYaml2(metadata));
  } catch {
  }
}
function readServerMetadata(serverName) {
  const MCP_ROOT2 = join7(BASE_DIR2, "..");
  const metadataPath = join7(MCP_ROOT2, serverName, "metadata.yaml");
  if (!existsSync6(metadataPath)) return null;
  try {
    return parseYaml2(readFileSync4(metadataPath, "utf-8"));
  } catch {
    return null;
  }
}
async function sendRequest(timeout, server2, method, params) {
  const requestId = ++server2.requestId;
  const request = {
    jsonrpc: "2.0",
    id: requestId,
    method,
    ...params && { params }
  };
  if (server2.url) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    try {
      const headers = {
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream",
        ...server2.headers || {}
      };
      if (server2.metadata?.sessionId) {
        headers["Mcp-Session-Id"] = server2.metadata.sessionId;
      }
      const response = await fetch(server2.url, {
        method: "POST",
        headers,
        body: JSON.stringify(request),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      const sessionId = response.headers.get("mcp-session-id");
      if (sessionId && server2.metadata) {
        server2.metadata.sessionId = sessionId;
      }
      const contentType = response.headers.get("content-type") || "";
      let result;
      if (contentType.includes("text/event-stream")) {
        const text = await response.text();
        const dataLines = text.split("\n").filter((l) => l.startsWith("data: ")).map((l) => l.slice(6));
        const lastData = dataLines[dataLines.length - 1];
        if (!lastData) throw new Error("No data in SSE response");
        result = JSON.parse(lastData);
      } else {
        result = await response.json();
      }
      if (result.error) throw new Error(result.error.message || JSON.stringify(result.error));
      return result.result;
    } catch (e) {
      clearTimeout(timeoutId);
      if (e.name === "AbortError") throw new Error("Request timeout");
      throw e;
    }
  }
  return new Promise((resolve2, reject) => {
    const { stdin, stdout } = server2.process;
    if (!stdin || !stdout) {
      reject(new Error("Process streams not available"));
      return;
    }
    const rl = createInterface({ input: stdout });
    const timeoutId = setTimeout(() => {
      rl.close();
      reject(new Error("Request timeout"));
    }, timeout);
    const handleLine = (line) => {
      if (!line.trim()) return;
      if (!line.startsWith("{")) {
        log(`  [stdout] ${line}`);
        const portMatch = line.match(/\[PortRegistry\] Allocated port (\d+)/);
        if (portMatch && server2.metadata) {
          server2.metadata.cdpPort = parseInt(portMatch[1], 10);
        }
        return;
      }
      try {
        const response = JSON.parse(line);
        if (response.id !== requestId) return;
        clearTimeout(timeoutId);
        rl.removeListener("line", handleLine);
        rl.close();
        if (response.error) {
          reject(new Error(response.error.message || JSON.stringify(response.error)));
        } else {
          resolve2(response.result);
        }
      } catch {
      }
    };
    rl.on("line", handleLine);
    stdin.write(JSON.stringify(request) + "\n");
  });
}
async function initializeServer(server2, timeout) {
  const result = await sendRequest(timeout, server2, "initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "mcp-manager", version: "2.0.0" }
  });
  if (server2.url) {
    const headers = {
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
      ...server2.headers || {}
    };
    if (server2.metadata?.sessionId) {
      headers["Mcp-Session-Id"] = server2.metadata.sessionId;
    }
    try {
      await fetch(server2.url, {
        method: "POST",
        headers,
        body: JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" })
      });
    } catch {
    }
  } else if (server2.process?.stdin) {
    server2.process.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");
  }
  return result;
}
async function listServerTools(server2, timeout) {
  const result = await sendRequest(timeout, server2, "tools/list");
  return result?.tools || [];
}
async function callServerTool(timeout, server2, toolName, args) {
  return sendRequest(timeout, server2, "tools/call", { name: toolName, arguments: args });
}
function needsShell(cmd) {
  if (process.platform !== "win32") return false;
  const lc = cmd.toLowerCase();
  return lc === "npx" || lc === "npm" || lc.endsWith(".cmd") || lc.endsWith(".bat");
}
async function startServer(name) {
  if (!(name in SERVERS)) return [false, `Unknown server: ${name}`];
  if (name in RUNNING) return [false, `Server already running: ${name}`];
  const config = SERVERS[name];
  if (config.enabled === false) return [false, `Server is disabled: ${name}`];
  const reqTimeout = config.timeout || 6e4;
  if (config.url) {
    try {
      const server2 = {
        url: config.url,
        headers: config.headers,
        startedAt: (/* @__PURE__ */ new Date()).toISOString(),
        lastActivity: Date.now(),
        toolsCount: 0,
        requestId: 0,
        metadata: { transport: "http" }
      };
      try {
        await initializeServer(server2, reqTimeout);
      } catch (e) {
        return [false, `Failed to initialize HTTP server: ${e.message}`];
      }
      try {
        const tools2 = await listServerTools(server2, reqTimeout);
        TOOLS[name] = tools2;
        server2.toolsCount = tools2.length;
        for (const tool of tools2) {
          if (tool.name) {
            TOOL_MAP[`${name}:${tool.name}`] = name;
            TOOL_MAP[tool.name] = name;
          }
        }
      } catch (e) {
        return [false, `Failed to list tools: ${e.message}`];
      }
      RUNNING[name] = server2;
      saveToolsToMetadata(name, TOOLS[name]);
      updateCapabilitiesCache();
      return [true, `Connected to ${name} (HTTP) with ${server2.toolsCount} tools`];
    } catch (e) {
      return [false, `Failed to connect to ${name}: ${e.message}`];
    }
  }
  if (!config.command) return [false, `Server ${name} has no command or url configured`];
  try {
    const cmd = config.command;
    const args = config.args || [];
    const env = { ...process.env, ...config.env || {} };
    const startupDelay = config.startup_delay || 2e3;
    const proc = spawn(cmd, args, {
      stdio: ["pipe", "pipe", "pipe"],
      env,
      shell: needsShell(cmd),
      cwd: BASE_DIR2
    });
    const server2 = {
      process: proc,
      startedAt: (/* @__PURE__ */ new Date()).toISOString(),
      lastActivity: Date.now(),
      toolsCount: 0,
      requestId: 0,
      metadata: { transport: "stdio" }
    };
    await new Promise((resolve2) => setTimeout(resolve2, startupDelay));
    try {
      await initializeServer(server2, reqTimeout);
    } catch (e) {
      proc.kill();
      return [false, `Failed to initialize: ${e.message}`];
    }
    try {
      const tools2 = await listServerTools(server2, reqTimeout);
      TOOLS[name] = tools2;
      server2.toolsCount = tools2.length;
      for (const tool of tools2) {
        if (tool.name) {
          TOOL_MAP[`${name}:${tool.name}`] = name;
          TOOL_MAP[tool.name] = name;
        }
      }
    } catch (e) {
      proc.kill();
      return [false, `Failed to list tools: ${e.message}`];
    }
    RUNNING[name] = server2;
    saveToolsToMetadata(name, TOOLS[name]);
    updateCapabilitiesCache();
    return [true, `Started ${name} with ${server2.toolsCount} tools`];
  } catch (e) {
    return [false, `Failed to start ${name}: ${e.message}`];
  }
}
function stopServer(name) {
  if (!(name in RUNNING)) return [false, `Server not running: ${name}`];
  try {
    const server2 = RUNNING[name];
    if (server2.process) server2.process.kill();
    if (name in TOOLS) {
      for (const tool of TOOLS[name]) {
        delete TOOL_MAP[`${name}:${tool.name}`];
        if (TOOL_MAP[tool.name] === name) delete TOOL_MAP[tool.name];
      }
      delete TOOLS[name];
    }
    delete RUNNING[name];
    const transport = server2.url ? "HTTP" : "stdio";
    return [true, `Stopped ${name} (${transport})`];
  } catch (e) {
    return [false, `Failed to stop ${name}: ${e.message}`];
  }
}
async function restartServer(name) {
  if (name in RUNNING) stopServer(name);
  return startServer(name);
}
async function autoStartServers() {
  for (const [name, config] of Object.entries(SERVERS)) {
    if (config.auto_start && config.enabled !== false) {
      log(`Auto-starting ${name}...`);
      const [success, msg] = await startServer(name);
      log(`  ${msg}`);
    }
  }
  updateCapabilitiesCache();
  const totalTools = Object.values(TOOLS).flat().length;
  log(`Capabilities cached: ${Object.keys(RUNNING).length} servers, ${totalTools} tools`);
}
var server = new McpServer({
  name: "mcp-manager",
  version: "2.0.0"
});
var PROJECT_NAME = null;
var ALLOWED_SERVERS = null;
function detectProjectContext() {
  const projectPath = process.env.MCPM_PROJECT_PATH || process.cwd();
  const mcpJsonPath = join7(projectPath, ".mcp.json");
  if (!existsSync6(mcpJsonPath)) {
    log(`No .mcp.json in ${projectPath} - no project filtering`);
    return;
  }
  try {
    const content = readFileSync4(mcpJsonPath, "utf-8");
    const config = JSON.parse(content);
    const mcpManager = config.mcpServers?.["mcp-manager"];
    if (mcpManager?.allowedServers && Array.isArray(mcpManager.allowedServers)) {
      ALLOWED_SERVERS = mcpManager.allowedServers;
      const parts = projectPath.replace(/\\/g, "/").split("/");
      PROJECT_NAME = parts[parts.length - 1] || null;
      log(`Project: ${PROJECT_NAME}, allowed servers: ${ALLOWED_SERVERS.join(", ")}`);
    } else {
      log(`No allowedServers in ${mcpJsonPath} - no project filtering`);
    }
  } catch (e) {
    log(`Failed to parse ${mcpJsonPath}: ${e.message}`);
  }
}
function isServerAllowed(name) {
  if (!ALLOWED_SERVERS) return true;
  return ALLOWED_SERVERS.includes(name);
}
function getContext() {
  return {
    SERVERS,
    RUNNING,
    TOOLS,
    TOOL_MAP,
    BASE_DIR: BASE_DIR2,
    SERVERS_FILE,
    log,
    loadServersConfig,
    loadCapabilitiesCache,
    updateCapabilitiesCache,
    saveServersConfig,
    startServer,
    stopServer,
    restartServer,
    callServerTool,
    readServerMetadata,
    projectName: PROJECT_NAME,
    allowedServers: ALLOWED_SERVERS,
    isServerAllowed,
    reloadProjectConfig: detectProjectContext
  };
}
var MCPM_DESCRIPTION = `MCP server manager - single tool for all operations.

## Query (read-only)
  list_servers   List all servers with status
  search         Search servers, tools, descriptions (query, auto_start?)
  details        Full info on one server (server)
  tools          List tools (server?)
  status         System health, memory
  help           Show operations

## Call (proxy)
  call           Execute tool on backend (server, tool, arguments?)

## Admin (modify)
  start/stop/restart   Server lifecycle (server)
  enable         Enable/disable server (server, enabled)
  add            Register server (server, command, args?, description?)
  remove         Unregister server (server)
  reload         Reload config
  discover       Scan for new servers
  usage          Project usage
  ram            RAM details`;
server.tool(
  "mcpm",
  MCPM_DESCRIPTION,
  {
    operation: z.string().describe("Operation: list_servers, search, details, tools, status, help, call, start, stop, restart, enable, add, remove, reload, discover, usage, ram"),
    server: z.string().optional().describe("Server name (for server-specific operations)"),
    query: z.string().optional().describe("Search query (for search operation)"),
    tool: z.string().optional().describe("Tool name (for call operation)"),
    arguments: z.record(z.any()).optional().describe("Tool arguments (for call operation)"),
    enabled: z.boolean().optional().describe("Enable/disable flag (for enable operation)"),
    auto_start: z.boolean().optional().describe("Auto-start flag"),
    command: z.string().optional().describe("Command (for add operation)"),
    args: z.array(z.string()).optional().describe("Command args (for add operation)"),
    description: z.string().optional().describe("Description (for add operation)"),
    env: z.record(z.string()).optional().describe("Environment variables (for add operation)"),
    tags: z.array(z.string()).optional().describe("Tags (for add operation)")
  },
  async (params) => {
    const ctx = getContext();
    const operation = params.operation;
    switch (operation) {
      // Query operations
      case "list_servers":
      case "list":
        return listServers(ctx);
      case "search":
      case "find":
        return search(ctx, params);
      case "details":
      case "info":
        return details(ctx, params);
      case "tools":
        return tools(ctx, params);
      case "status":
        return status(ctx);
      case "help":
        return help();
      // Call operation
      case "call":
        return call(ctx, params);
      // Admin operations
      case "start":
        return start(ctx, params);
      case "stop":
        return stop(ctx, params);
      case "restart":
        return restart(ctx, params);
      case "enable":
        return enable(ctx, params);
      case "add":
        return add(ctx, params);
      case "remove":
        return remove(ctx, params);
      case "reload":
        return reload(ctx);
      case "discover":
        return discover(ctx);
      case "usage":
        return usage(ctx);
      case "ram":
        return ram(ctx);
      default:
        return {
          content: [{
            type: "text",
            text: `Unknown operation: ${operation}. Use mcpm(operation="help") to see available operations.`
          }]
        };
    }
  }
);
var MCPM_INSTRUCTIONS = {
  "mcpm-only-in-mcp-json": {
    name: "Only mcpm in .mcp.json",
    keywords: ["mcp.json", "mcp server", "add mcp", "remote mcp", "http mcp", "configure mcp"],
    content: `# Rule: Only mcpm in .mcp.json

## WHY

The user NEVER wants any MCP server entry in .mcp.json except mcp-manager (mcpm). All servers - local stdio, remote HTTP, SSE - must go through mcpm. This keeps a single source of truth and avoids config sprawl.

## What To Do

- **NEVER** add a direct MCP server entry to .mcp.json (no \`"type": "http"\`, no \`"command": "python"\`, etc.)
- **ALWAYS** add servers to mcpm's \`servers\` list in .mcp.json AND configure them in servers.yaml
- If a server needs HTTP/SSE transport, build that capability into mcpm (proxy mode)
- If mcpm can't handle a server type yet, extend mcpm - don't work around it

## .mcp.json Format (always)

\`\`\`json
{
  "mcpServers": {
    "mcp-manager": {
      "command": "node",
      "args": ["path/to/mcp-manager/build/index.js"],
      "env": { "..." : "..." },
      "servers": ["server1", "server2"]
    }
  }
}
\`\`\`

No other top-level entries. Ever.`
  },
  "mcpm-reload-flow": {
    name: "mcpm reload flow",
    keywords: ["reload mcp", "restart mcp", "mcp not working", "reconnect mcp", "mcp config", "mcp changed", "new mcp server"],
    content: `# How to Reload mcpm After Config Changes

## WHY

When servers.yaml or .mcp.json changes, the running mcpm process has stale config. Users don't need to restart Claude Code - they just need to reconnect mcpm.

## Reload Flow

Tell the user to run \`/mcp\`, select \`mcp-manager\`, and click reconnect. This reloads the mcpm process with the latest build and config. Then \`mcpm reload\` picks up servers.yaml changes.

**Steps:**
1. \`/mcp\` -> select mcp-manager -> Reconnect
2. \`mcpm reload\` (picks up servers.yaml changes)
3. \`mcpm start <server>\` (start any new servers)

## NEVER

- Never tell the user to restart Claude Code for mcpm changes
- Never add MCP servers directly to .mcp.json (only mcpm goes there)`
  }
};
function setupInstructions() {
  const home = process.env.HOME || process.env.USERPROFILE || "";
  if (!home) return;
  const instructionsDir = join7(home, ".claude", "instructions", "UserPromptSubmit");
  const hasInstructionManager = existsSync6(instructionsDir);
  if (hasInstructionManager) {
    let created = 0;
    for (const [id, inst] of Object.entries(MCPM_INSTRUCTIONS)) {
      const filePath = join7(instructionsDir, `${id}.md`);
      if (existsSync6(filePath)) continue;
      const frontmatter = [
        "---",
        `id: ${id}`,
        `name: ${inst.name}`,
        "keywords:",
        ...inst.keywords.map((k) => `  - ${k}`),
        "trigger: always",
        "---",
        ""
      ].join("\n");
      try {
        writeFileSync3(filePath, frontmatter + inst.content + "\n", "utf8");
        created++;
        log(`SETUP: Created instruction ${id}`);
      } catch (e) {
        log(`SETUP: Failed to create instruction ${id}: ${e.message}`);
      }
    }
    if (created > 0) log(`SETUP: Created ${created} instruction(s) in ${instructionsDir}`);
  } else {
    const claudeMdPath = join7(home, ".claude", "CLAUDE.md");
    if (!existsSync6(claudeMdPath)) return;
    try {
      const content = readFileSync4(claudeMdPath, "utf8");
      if (content.includes("mcpm-only-in-mcp-json") || content.includes("Only mcpm in .mcp.json")) return;
      const note = `

## mcpm Rules (auto-added by mcp-manager)

- Only mcpm goes in .mcp.json - never add direct MCP server entries
- To reload mcpm: \`/mcp\` -> select mcp-manager -> Reconnect (never restart Claude Code)
- All servers configured in servers.yaml, listed in .mcp.json servers array
`;
      writeFileSync3(claudeMdPath, content + note, "utf8");
      log("SETUP: Added mcpm rules to CLAUDE.md (no instruction-manager found)");
    } catch (e) {
      log(`SETUP: Failed to update CLAUDE.md: ${e.message}`);
    }
  }
}
async function main() {
  log("=== MCP Manager v2.0 starting ===");
  loadEnv(BASE_DIR2);
  const serverCount = loadServersConfig();
  log(`Loaded ${serverCount} servers from ${SERVERS_FILE}`);
  detectProjectContext();
  const hooksCount = loadHooks(BASE_DIR2);
  log(`Loaded ${hooksCount} hooks from hooks.yaml`);
  setupInstructions();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  log("MCP Manager connected to Claude");
  startIdleChecker();
  autoStartServers().catch((e) => log(`Auto-start error: ${e.message}`));
}
main().catch(console.error);
