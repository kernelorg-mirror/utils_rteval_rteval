#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   rteval MCP Server tests - per-CPU statistics
#
#   Copyright 2026   John Kacur <jkacur@redhat.com>
#
"""Test the get_per_cpu_stats tool."""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path to import rteval_server module
sys.path.insert(0, str(Path(__file__).parent.parent))
from rteval_server import call_tool


async def main():
    print("Testing get_per_cpu_stats tool")
    print("=" * 60)

    # Find test data - use any available rteval result
    rteval_dir = Path(__file__).parent.parent.parent
    test_files = list(rteval_dir.glob("rteval-*/summary.xml"))

    if not test_files:
        print(f"✗ No rteval result files found in {rteval_dir}")
        print("Please run rteval to generate test data first.")
        sys.exit(1)

    # Use the most recent file
    test_file = sorted(test_files)[-1]
    print(f"\nUsing test file: {test_file.parent.name}/summary.xml\n")

    # Test 1: Basic per-CPU stats (sorted by maximum)
    print("1. Basic per-CPU stats sorted by maximum latency...")
    try:
        result = await call_tool("get_per_cpu_stats", {
            "file_path": str(test_file)
        })
        output = result[0].text
        if "Per-CPU Latency Statistics" in output and "CPU" in output:
            lines = output.split('\n')[:20]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 2: Show only top 5 worst CPUs
    print("\n2. Show top 5 worst CPUs by maximum latency...")
    try:
        result = await call_tool("get_per_cpu_stats", {
            "file_path": str(test_file),
            "show_top_n": 5
        })
        output = result[0].text
        if "Total CPUs: 5" in output or "5" in output:
            lines = output.split('\n')[:15]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 3: Sort by mean latency
    print("\n3. Sort CPUs by mean latency...")
    try:
        result = await call_tool("get_per_cpu_stats", {
            "file_path": str(test_file),
            "sort_by": "mean",
            "show_top_n": 3
        })
        output = result[0].text
        if "Sorted by: mean" in output:
            lines = output.split('\n')[:15]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 4: Highlight CPUs above threshold
    print("\n4. Highlight CPUs with max latency > 1000 µs...")
    try:
        result = await call_tool("get_per_cpu_stats", {
            "file_path": str(test_file),
            "highlight_threshold": 1000,
            "show_top_n": 10
        })
        output = result[0].text
        if "Highlighting CPUs" in output:
            lines = output.split('\n')[:18]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 5: Sort by standard deviation to find most variable CPUs
    print("\n5. Find CPUs with highest variability (std deviation)...")
    try:
        result = await call_tool("get_per_cpu_stats", {
            "file_path": str(test_file),
            "sort_by": "standard_deviation",
            "show_top_n": 5
        })
        output = result[0].text
        if "Sorted by: standard_deviation" in output:
            lines = output.split('\n')[:15]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ All get_per_cpu_stats tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
