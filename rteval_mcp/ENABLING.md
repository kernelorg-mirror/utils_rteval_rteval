# Enabling the rteval MCP server

Installing the `rteval-mcp` package puts the server on your `PATH` as
`rteval-mcp-server`, but it does **not** register the server with any MCP
client. MCP servers are launched on demand by the client, so you point your
client at the server once; there is no daemon or system service to start.

## Install

    sudo dnf install rteval-mcp

This provides:

- `/usr/bin/rteval-mcp-server` — the server executable, on your `PATH`
- the `rteval_mcp` Python module
- the `python3-mcp` runtime dependency

## Register with Claude Code

Run this once:

    claude mcp add rteval-mcp -- rteval-mcp-server

The tools then appear with the `mcp__rteval-mcp__` prefix. There is nothing
to keep running: Claude Code spawns `rteval-mcp-server` when it needs it and
stops it when the session ends.

## Register with another MCP client

Any stdio-capable MCP client works. Add an entry equivalent to the sample in
`mcp.json.example`: run the command `rteval-mcp-server` with no arguments.
For example, a project-scoped `.mcp.json`:

    {
      "mcpServers": {
        "rteval-mcp": {
          "command": "rteval-mcp-server",
          "args": []
        }
      }
    }

## Running from a source checkout (no install)

If you are working from the git tree instead of an installed package, you do
not need the entry point on `PATH`. Run the module directly from the repo
root, where the working directory is on `sys.path`:

    {
      "mcpServers": {
        "rteval-mcp": {
          "command": "python3",
          "args": ["-m", "rteval_mcp"]
        }
      }
    }

This is what the repository's own `.mcp.json` uses.
