#!/usr/bin/env python3
"""Test the new query/filter tools."""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path to import server module
sys.path.insert(0, str(Path(__file__).parent.parent))
from server import extract_rteval_data


async def test_find_best_worst():
    """Test the find_best_worst functionality."""
    print("Testing find_best_worst logic...")
    print("=" * 60)

    # Search for XML files relative to script location
    # From tests/ -> mcp-server/ -> rteval/
    directory = Path(__file__).parent.parent.parent
    metric = "maximum"
    count = 3

    files = list(directory.glob("rteval-*/summary.xml"))

    print(f"Found {len(files)} XML files")

    # Parse and collect metrics
    results_with_metrics = []
    for file_path in files:
        try:
            data = extract_rteval_data(str(file_path))

            # Extract the requested metric
            metric_value = None
            for mtype in ["timerlat", "cyclictest"]:
                if mtype in data["measurements"]:
                    metric_data = data["measurements"][mtype].get(metric)
                    if metric_data:
                        try:
                            metric_value = float(metric_data["value"])
                            break
                        except ValueError:
                            pass

            if metric_value is not None:
                results_with_metrics.append((data, metric_value))
                print(f"  {Path(data['file']).name}: {metric_value:.2f} µs")

        except Exception as e:
            print(f"  Error parsing {file_path.name}: {e}")
            continue

    if not results_with_metrics:
        print(f"No results found with {metric} metric")
        return

    # Sort by metric value
    results_with_metrics.sort(key=lambda x: x[1])

    print(f"\nBEST {min(count, len(results_with_metrics))} Results (lowest {metric}):")
    print("-" * 60)
    for i, (data, metric_val) in enumerate(results_with_metrics[:count], 1):
        print(f"{i}. {Path(data['file']).name}")
        print(f"   {metric.capitalize()}: {metric_val:.2f} µs")
        if "kernel" in data["system_info"]:
            print(f"   Kernel: {data['system_info']['kernel']}")

    print(f"\nWORST {min(count, len(results_with_metrics))} Results (highest {metric}):")
    print("-" * 60)
    for i, (data, metric_val) in enumerate(reversed(results_with_metrics[-count:]), 1):
        print(f"{i}. {Path(data['file']).name}")
        print(f"   {metric.capitalize()}: {metric_val:.2f} µs")
        if "kernel" in data["system_info"]:
            print(f"   Kernel: {data['system_info']['kernel']}")


async def test_filter_results():
    """Test the filter_results functionality."""
    print("\n\nTesting filter_results logic...")
    print("=" * 60)

    # Search for XML files relative to script location
    directory = Path(__file__).parent.parent.parent
    kernel_pattern = "7.0"

    files = list(directory.glob("rteval-*/summary.xml"))

    print(f"Filtering for kernel pattern: {kernel_pattern}")
    print(f"Searching {len(files)} XML files\n")

    # Parse and filter
    filtered = []
    for file_path in files:
        try:
            data = extract_rteval_data(str(file_path))

            # Apply kernel filter
            if kernel_pattern and kernel_pattern.lower() not in data["system_info"].get("kernel", "").lower():
                continue

            filtered.append(data)

        except Exception:
            continue

    print(f"Filtered Results ({len(filtered)} of {len(files)} files matched):\n")

    for data in filtered:
        print(f"{Path(data['file']).name}:")
        if "date" in data["run_info"]:
            print(f"  Date: {data['run_info']['date']}")
        if "kernel" in data["system_info"]:
            print(f"  Kernel: {data['system_info']['kernel']}")

        # Show key metrics
        for mtype in ["timerlat", "cyclictest"]:
            if mtype in data["measurements"]:
                meas = data["measurements"][mtype]
                if "maximum" in meas:
                    print(f"  Max latency: {meas['maximum']['value']} {meas['maximum']['unit']}")
                if "mean" in meas:
                    print(f"  Mean latency: {meas['mean']['value']} {meas['mean']['unit']}")
                break
        print()


async def main():
    """Run all tests."""
    await test_find_best_worst()
    await test_filter_results()


if __name__ == "__main__":
    asyncio.run(main())
