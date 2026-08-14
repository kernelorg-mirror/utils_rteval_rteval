#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   rteval MCP Server entry point
#
#   Copyright 2026   John Kacur <jkacur@redhat.com>
#
"""Entry point for running rteval MCP server as a module."""

import sys
import asyncio
from pathlib import Path

# Add package directory to path for development mode
package_dir = Path(__file__).parent
sys.path.insert(0, str(package_dir))

from rteval_server import app, stdio_server


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
