# rteval MCP Server

An MCP (Model Context Protocol) server for querying and analyzing rteval test results.

## Purpose

This MCP server provides tools to:
- List and discover rteval result files
- Parse rteval XML/JSON output
- Compare multiple test runs
- Query historical performance data
- Analyze latency trends across runs

## Target Users

System administrators, QE engineers, and developers who run rteval regularly for:
- Real-time kernel validation
- Performance regression testing
- CI/CD pipelines
- System certification

## Current Status

**Prototype/Development** - This is a first attempt at building an MCP server for rteval.
The initial focus is on multi-run analysis rather than single-result querying.

## Installation

On Fedora:
```bash
sudo dnf install python3-mcp python3-mcp+cli python3-lxml
```

## Available Tools

- **list_results**: List rteval result files in a directory
- **parse_result**: Parse an rteval XML result file and extract key metrics
- **compare_results**: Compare two rteval result files side-by-side
- **list_logs**: List available log files in an rteval result directory
- **read_log**: Read log content with optional filtering (head/tail/grep)

## Usage

### Testing the Server Directly

```bash
python3 test_tools.py
```

### Using with Claude Code

The server is configured as a Claude Code plugin. After installation:

1. The server is registered in `~/.claude/plugins/installed_plugins.json`
2. Enabled in `~/.claude/settings.json`
3. Restart Claude Code to load the plugin
4. Tools will be available with the prefix: `mcp__plugin_rteval-mcp_rteval__`

Example:
```
list rteval results in ~/src/rteval
```

### Using with MCP Inspector

```bash
mcp dev server.py
```

## Development

This is a work in progress. The MCP server is being developed in a branch of the
main rteval repository and may be split into a separate repository later.
