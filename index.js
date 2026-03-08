#!/usr/bin/env node

/**
 * ENCODE Toolkit — npm wrapper for the Python MCP server.
 *
 * This is a thin wrapper that spawns the Python-based encode-toolkit
 * MCP server using uvx. The actual server code is in the encode-toolkit
 * PyPI package.
 *
 * Usage:
 *   npx encode-toolkit
 *
 * Or in MCP client config:
 *   { "command": "npx", "args": ["encode-toolkit"] }
 */

const { spawn } = require("child_process");

// Try uvx first (recommended), fall back to encode-toolkit command
function startServer() {
  const uvx = spawn("uvx", ["encode-toolkit"], {
    stdio: "inherit",
    shell: process.platform === "win32",
  });

  uvx.on("error", () => {
    // uvx not found, try direct command
    const direct = spawn("encode-toolkit", [], {
      stdio: "inherit",
      shell: process.platform === "win32",
    });

    direct.on("error", () => {
      console.error(
        "Error: Could not start encode-toolkit server.\n\n" +
        "Please install the Python package first:\n" +
        "  pip install encode-toolkit\n\n" +
        "Or install uv for automatic management:\n" +
        "  curl -LsSf https://astral.sh/uv/install.sh | sh"
      );
      process.exit(1);
    });

    direct.on("exit", (code) => process.exit(code ?? 0));
  });

  uvx.on("exit", (code) => process.exit(code ?? 0));
}

startServer();
