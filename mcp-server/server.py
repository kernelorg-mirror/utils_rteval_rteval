#!/usr/bin/env python3
"""
rteval MCP Server

An MCP server for querying and analyzing rteval test results.
Provides tools to list, parse, and compare rteval XML result files.
"""

import os
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Initialize the MCP server
app = Server("rteval-mcp-server")


def extract_rteval_data(file_path: str) -> dict[str, Any]:
    """Extract key data from an rteval XML file for comparison."""
    tree = ET.parse(file_path)
    root = tree.getroot()

    data = {
        "file": file_path,
        "rteval_version": root.get("version", "unknown"),
        "run_info": {},
        "system_info": {},
        "measurements": {}
    }

    # Run information
    runinfo = root.find("run_info")
    if runinfo is not None:
        data["run_info"] = {
            "days": int(runinfo.get("days", "0")),
            "hours": int(runinfo.get("hours", "0")),
            "minutes": int(runinfo.get("minutes", "0")),
            "seconds": int(runinfo.get("seconds", "0")),
        }
        date_elem = runinfo.find("date")
        time_elem = runinfo.find("time")
        if date_elem is not None and time_elem is not None:
            data["run_info"]["date"] = date_elem.text
            data["run_info"]["time"] = time_elem.text

    # System information
    sysinfo = root.find("SystemInfo")
    if sysinfo is not None:
        uname = sysinfo.find("uname")
        if uname is not None:
            for elem in ["baseos", "node", "arch", "kernel"]:
                node = uname.find(elem)
                if node is not None:
                    if elem == "kernel":
                        data["system_info"]["kernel"] = node.text
                        data["system_info"]["is_RT"] = node.get("is_RT", "0") == "1"
                    else:
                        data["system_info"][elem] = node.text

    # Timerlat measurements
    timerlat = root.find(".//timerlat")
    if timerlat is not None:
        data["measurements"]["timerlat"] = {}
        stats = timerlat.find(".//statistics")
        if stats is not None:
            for stat in stats:
                data["measurements"]["timerlat"][stat.tag] = {
                    "value": stat.text,
                    "unit": stat.get("unit", "")
                }

    # Cyclictest measurements
    cyclictest = root.find(".//cyclictest")
    if cyclictest is not None:
        data["measurements"]["cyclictest"] = {}
        stats = cyclictest.find(".//statistics")
        if stats is not None:
            for stat in stats:
                data["measurements"]["cyclictest"][stat.tag] = {
                    "value": stat.text,
                    "unit": stat.get("unit", "")
                }

    return data


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for rteval analysis."""
    return [
        Tool(
            name="list_results",
            description="List rteval result files in a directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to search for rteval results (default: current directory)",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern to match (default: *.xml)",
                        "default": "*.xml",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="parse_result",
            description="Parse an rteval XML result file and extract key metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the rteval XML result file",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="compare_results",
            description="Compare two rteval result files",
            inputSchema={
                "type": "object",
                "properties": {
                    "file1": {
                        "type": "string",
                        "description": "Path to the first rteval XML result file",
                    },
                    "file2": {
                        "type": "string",
                        "description": "Path to the second rteval XML result file",
                    },
                },
                "required": ["file1", "file2"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""

    if name == "list_results":
        directory = arguments.get("directory", ".")
        pattern = arguments.get("pattern", "*.xml")

        try:
            path = Path(directory)
            if not path.exists():
                return [TextContent(
                    type="text",
                    text=f"Error: Directory '{directory}' does not exist"
                )]

            # Find matching files
            files = list(path.glob(pattern))

            if not files:
                return [TextContent(
                    type="text",
                    text=f"No files matching '{pattern}' found in '{directory}'"
                )]

            # Sort by modification time (newest first)
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            result = f"Found {len(files)} rteval result file(s) in '{directory}':\n\n"
            for f in files:
                mtime = f.stat().st_mtime
                size = f.stat().st_size
                result += f"  {f.name}\n"
                result += f"    Path: {f.absolute()}\n"
                result += f"    Size: {size:,} bytes\n"
                result += f"    Modified: {Path(f).stat().st_mtime}\n\n"

            return [TextContent(type="text", text=result)]

        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error listing results: {str(e)}"
            )]

    elif name == "parse_result":
        file_path = arguments["file_path"]

        try:
            path = Path(file_path)
            if not path.exists():
                return [TextContent(
                    type="text",
                    text=f"Error: File '{file_path}' does not exist"
                )]

            # Parse XML
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Extract basic information
            result = f"rteval Result Summary for: {path.name}\n"
            result += "=" * 60 + "\n\n"

            # Extract rteval version
            rteval_version = root.get("version", "unknown")
            result += f"rteval version: {rteval_version}\n\n"

            # Run information
            runinfo = root.find("run_info")
            if runinfo is not None:
                result += "Run Information:\n"
                result += f"  Duration: {runinfo.get('days', '0')} days, "
                result += f"{runinfo.get('hours', '0')} hours, "
                result += f"{runinfo.get('minutes', '0')} minutes, "
                result += f"{runinfo.get('seconds', '0')} seconds\n"

                date_elem = runinfo.find("date")
                time_elem = runinfo.find("time")
                if date_elem is not None and time_elem is not None:
                    result += f"  Started: {date_elem.text} {time_elem.text}\n"
                result += "\n"

            # System information
            sysinfo = root.find("SystemInfo")
            if sysinfo is not None:
                uname = sysinfo.find("uname")
                if uname is not None:
                    result += "System Information:\n"
                    for elem in ["baseos", "node", "arch", "kernel"]:
                        node = uname.find(elem)
                        if node is not None:
                            if elem == "kernel":
                                is_rt = node.get("is_RT", "0")
                                result += f"  {elem}: {node.text} (RT: {'Yes' if is_rt == '1' else 'No'})\n"
                            else:
                                result += f"  {elem}: {node.text}\n"
                    result += "\n"

            # Timerlat measurements
            timerlat = root.find(".//timerlat")
            if timerlat is not None:
                result += "Timerlat Measurements:\n"
                cmd_line = timerlat.get("command_line", "")
                result += f"  Command: {cmd_line}\n\n"

                stats = timerlat.find(".//statistics")
                if stats is not None:
                    result += "  Statistics:\n"
                    for stat in stats:
                        unit = stat.get("unit", "")
                        unit_str = f" {unit}" if unit else ""
                        result += f"    {stat.tag}: {stat.text}{unit_str}\n"
                result += "\n"

            # Cyclictest measurements (if present instead of timerlat)
            cyclictest = root.find(".//cyclictest")
            if cyclictest is not None:
                result += "Cyclictest Measurements:\n"
                cmd_line = cyclictest.get("command_line", "")
                result += f"  Command: {cmd_line}\n\n"

                stats = cyclictest.find(".//statistics")
                if stats is not None:
                    result += "  Statistics:\n"
                    for stat in stats:
                        unit = stat.get("unit", "")
                        unit_str = f" {unit}" if unit else ""
                        result += f"    {stat.tag}: {stat.text}{unit_str}\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

        except ET.ParseError as e:
            return [TextContent(
                type="text",
                text=f"Error parsing XML file: {str(e)}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error reading result file: {str(e)}"
            )]

    elif name == "compare_results":
        file1 = arguments["file1"]
        file2 = arguments["file2"]

        try:
            # Check if files exist
            if not Path(file1).exists():
                return [TextContent(
                    type="text",
                    text=f"Error: File '{file1}' does not exist"
                )]
            if not Path(file2).exists():
                return [TextContent(
                    type="text",
                    text=f"Error: File '{file2}' does not exist"
                )]

            # Extract data from both files
            data1 = extract_rteval_data(file1)
            data2 = extract_rteval_data(file2)

            # Build comparison report
            result = "rteval Results Comparison\n"
            result += "=" * 60 + "\n\n"

            result += f"File 1: {Path(file1).name}\n"
            result += f"File 2: {Path(file2).name}\n\n"

            # Compare system information
            result += "System Comparison:\n"
            result += "-" * 60 + "\n"

            sys1 = data1.get("system_info", {})
            sys2 = data2.get("system_info", {})

            for key in ["baseos", "node", "arch", "kernel", "is_RT"]:
                val1 = sys1.get(key, "N/A")
                val2 = sys2.get(key, "N/A")
                if val1 != val2:
                    result += f"  {key}:\n"
                    result += f"    File 1: {val1}\n"
                    result += f"    File 2: {val2}\n"
                else:
                    result += f"  {key}: {val1}\n"
            result += "\n"

            # Compare run durations
            result += "Run Duration:\n"
            result += "-" * 60 + "\n"

            run1 = data1.get("run_info", {})
            run2 = data2.get("run_info", {})

            def format_duration(info):
                return f"{info.get('days', 0)}d {info.get('hours', 0)}h {info.get('minutes', 0)}m {info.get('seconds', 0)}s"

            result += f"  File 1: {format_duration(run1)}\n"
            result += f"  File 2: {format_duration(run2)}\n\n"

            # Compare measurements (timerlat or cyclictest)
            meas1 = data1.get("measurements", {})
            meas2 = data2.get("measurements", {})

            # Determine which measurement type to compare
            measurement_type = None
            if "timerlat" in meas1 and "timerlat" in meas2:
                measurement_type = "timerlat"
            elif "cyclictest" in meas1 and "cyclictest" in meas2:
                measurement_type = "cyclictest"

            if measurement_type:
                result += f"{measurement_type.capitalize()} Statistics Comparison:\n"
                result += "-" * 60 + "\n"

                stats1 = meas1.get(measurement_type, {})
                stats2 = meas2.get(measurement_type, {})

                # Key metrics to compare
                for metric in ["samples", "minimum", "maximum", "mean", "median", "standard_deviation"]:
                    if metric in stats1 and metric in stats2:
                        val1_data = stats1[metric]
                        val2_data = stats2[metric]

                        val1 = val1_data["value"]
                        val2 = val2_data["value"]
                        unit = val1_data.get("unit", "")

                        result += f"  {metric}:\n"
                        result += f"    File 1: {val1} {unit}\n"
                        result += f"    File 2: {val2} {unit}\n"

                        # Calculate difference for numeric values
                        try:
                            num1 = float(val1)
                            num2 = float(val2)
                            diff = num2 - num1
                            if diff > 0:
                                result += f"    Difference: +{diff:.2f} {unit} (File 2 is higher)\n"
                            elif diff < 0:
                                result += f"    Difference: {diff:.2f} {unit} (File 2 is lower)\n"
                            else:
                                result += f"    Difference: No change\n"

                            # Calculate percentage change for non-zero values
                            if num1 != 0 and metric != "samples":
                                pct_change = ((num2 - num1) / num1) * 100
                                result += f"    Percent change: {pct_change:+.2f}%\n"

                        except (ValueError, TypeError):
                            pass

                        result += "\n"
            else:
                result += "Measurement Comparison: Different measurement types used\n"
                result += f"  File 1: {', '.join(meas1.keys())}\n"
                result += f"  File 2: {', '.join(meas2.keys())}\n\n"

            return [TextContent(type="text", text=result)]

        except ET.ParseError as e:
            return [TextContent(
                type="text",
                text=f"Error parsing XML file: {str(e)}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error comparing results: {str(e)}"
            )]

    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
