#!/usr/bin/env python3
"""Integration tests for rteval MCP server.

Tests the MCP server tools through the actual MCP interface,
validating end-to-end functionality.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path to import server module
sys.path.insert(0, str(Path(__file__).parent.parent))
from server import call_tool, list_tools


def find_test_data():
    """Find available rteval result directories for testing."""
    # From tests/ -> mcp-server/ -> rteval/
    rteval_dir = Path(__file__).parent.parent.parent

    # Find rteval result directories (not rteval-build)
    result_dirs = sorted([
        d for d in rteval_dir.glob("rteval-*/")
        if d.is_dir() and d.name != "rteval-build" and (d / "summary.xml").exists()
    ])

    if not result_dirs:
        raise RuntimeError("No rteval result directories found for testing")

    return result_dirs


async def main():
    print("MCP Server Integration Tests")
    print("=" * 60)

    # Find test data
    try:
        result_dirs = find_test_data()
        test_dir = result_dirs[0]
        test_file = test_dir / "summary.xml"
        rteval_parent = test_dir.parent

        print(f"\nUsing test data: {test_dir.name}")
        print(f"Total result directories available: {len(result_dirs)}")
        print()
    except RuntimeError as e:
        print(f"✗ {e}")
        sys.exit(1)

    # Test 1: List available tools
    print("1. Testing list_tools()...")
    try:
        tools = await list_tools()
        print(f"✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:60]}...")
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 2: List results
    print("\n2. Testing list_results...")
    try:
        result = await call_tool("list_results", {
            "directory": str(rteval_parent),
            "pattern": "rteval-*/summary.xml"
        })
        output = result[0].text
        if "Found" in output and "file" in output:
            lines = output.split('\n')[:5]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 3: Parse a result
    print("\n3. Testing parse_result...")
    try:
        result = await call_tool("parse_result", {
            "file_path": str(test_file)
        })
        output = result[0].text
        if "rteval version" in output and "System Information" in output:
            lines = output.split('\n')[:10]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 4: List logs
    print("\n4. Testing list_logs...")
    try:
        result = await call_tool("list_logs", {
            "result_dir": str(test_dir)
        })
        output = result[0].text
        if "Log files" in output or "logs" in output.lower():
            lines = output.split('\n')[:8]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 5: Get percentiles (new histogram feature)
    print("\n5. Testing get_percentiles...")
    try:
        result = await call_tool("get_percentiles", {
            "file_path": str(test_file),
            "percentiles": [50, 95, 99, 99.9]
        })
        output = result[0].text
        if "Percentiles" in output and "P50" in output:
            lines = output.split('\n')[:12]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 6: Extract histogram (new feature)
    print("\n6. Testing extract_histogram...")
    try:
        result = await call_tool("extract_histogram", {
            "file_path": str(test_file),
            "include_per_cpu": False  # Keep output brief
        })
        output = result[0].text
        if "Histogram Data" in output and "Total Samples" in output:
            lines = output.split('\n')[:12]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 7: Filter results (query tools)
    print("\n7. Testing filter_results...")
    try:
        result = await call_tool("filter_results", {
            "directory": str(rteval_parent),
            "is_rt": False
        })
        output = result[0].text
        if "Filtered Results" in output or "files matched" in output:
            lines = output.split('\n')[:8]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 8: Find best/worst
    print("\n8. Testing find_best_worst...")
    try:
        result = await call_tool("find_best_worst", {
            "directory": str(rteval_parent),
            "metric": "maximum",
            "count": 3
        })
        output = result[0].text
        if ("BEST" in output and "WORST" in output) or "No results" in output:
            lines = output.split('\n')[:10]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    # Test 9: Get per-CPU stats
    print("\n9. Testing get_per_cpu_stats...")
    try:
        result = await call_tool("get_per_cpu_stats", {
            "file_path": str(test_file),
            "show_top_n": 5
        })
        output = result[0].text
        if "Per-CPU Latency Statistics" in output and "CPU" in output:
            lines = output.split('\n')[:12]
            print("✓ " + '\n  '.join(lines))
        else:
            print(f"✗ Unexpected output: {output[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ All MCP server integration tests passed!")
    print(f"\nTested with: {test_dir.name}")
    print(f"Total tools tested: 9")


if __name__ == "__main__":
    asyncio.run(main())
