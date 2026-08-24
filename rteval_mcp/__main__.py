#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   rteval MCP Server entry point
#
#   Copyright 2026   John Kacur <jkacur@redhat.com>
#
"""Entry point for running rteval MCP server as a module."""

import asyncio

from rteval_mcp.rteval_server import app, stdio_server


async def _run():
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def main():
    """Console-script entry point for the rteval MCP server."""
    asyncio.run(_run())


if __name__ == "__main__":
    main()
