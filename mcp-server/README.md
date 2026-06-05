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

```bash
pip install -r requirements.txt
```

## Usage

TBD - Server configuration and client usage instructions to be added.

## Development

This is a work in progress. The MCP server is being developed in a branch of the
main rteval repository and may be split into a separate repository later.
