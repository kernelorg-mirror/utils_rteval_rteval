# Dependencies

## Fedora Packages

Install these packages on Fedora:

```bash
sudo dnf install python3-mcp python3-mcp+cli
```

- **python3-mcp** - Base MCP SDK for building the server
- **python3-mcp+cli** - CLI tools for development and testing

## Python Dependencies

For parsing rteval results:
- **lxml** - XML parsing (should already be available on Fedora as `python3-lxml`)

```bash
sudo dnf install python3-lxml
```

## Optional

- **python3-mcp+rich** - For enhanced terminal output (optional)
