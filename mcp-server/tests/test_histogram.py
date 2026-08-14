#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
#   rteval MCP Server tests - histogram and percentile tools
#
#   Copyright 2026   John Kacur <jkacur@redhat.com>
#
"""
Test script for histogram extraction and percentile calculation.
"""

import sys
from pathlib import Path

# Add parent directory to path to import server module
sys.path.insert(0, str(Path(__file__).parent.parent))
from server import extract_histogram_data, calculate_percentiles

# Find test file relative to script location
# From tests/ -> mcp-server/ -> rteval/
script_dir = Path(__file__).parent
rteval_dir = script_dir.parent.parent

# Find any rteval result directory with summary.xml
test_files = list(rteval_dir.glob("rteval-*/summary.xml"))
if not test_files:
    print("ERROR: No rteval result files found in", rteval_dir)
    print("Please run rteval to generate test data first.")
    sys.exit(1)

# Use the most recent file
test_file = sorted(test_files)[-1]
print(f"Using test file: {test_file.parent.name}/summary.xml\n")

print("Testing histogram extraction...")
print("=" * 60)

# Extract histogram data
histogram_data = extract_histogram_data(str(test_file))

# Check system histogram
if histogram_data["system_histogram"]:
    sys_hist = histogram_data["system_histogram"]
    print(f"\nSystem-Wide Histogram:")
    print(f"  Total Buckets: {sys_hist['nbuckets']}")
    print(f"  Total Samples: {sys_hist['total_samples']:,}")
    print(f"  Latency Range: {sys_hist['buckets'][0]['latency_us']} - {sys_hist['buckets'][-1]['latency_us']} µs")

    # Calculate percentiles
    percentiles = [50, 90, 95, 99, 99.9, 99.99]
    result = calculate_percentiles(sys_hist["buckets"], percentiles)

    print(f"\nSystem-Wide Percentiles:")
    for p in percentiles:
        key = f"P{p}"
        if key in result:
            print(f"  {key:>7}: {result[key]:>6} µs")

# Check per-CPU histograms
if histogram_data["per_cpu_histograms"]:
    print(f"\nPer-CPU Histograms ({len(histogram_data['per_cpu_histograms'])} CPUs):")

    # Show first 3 CPUs in detail
    for cpu_hist in histogram_data["per_cpu_histograms"][:3]:
        cpu_id = cpu_hist["cpu_id"]
        total = cpu_hist["total_samples"]
        max_lat = cpu_hist["buckets"][-1]["latency_us"] if cpu_hist["buckets"] else 0

        print(f"\n  CPU {cpu_id}:")
        print(f"    Total Samples: {total:,}")
        print(f"    Max Latency: {max_lat} µs")

        # Calculate per-CPU percentiles
        cpu_percentiles = calculate_percentiles(cpu_hist["buckets"], [50, 95, 99, 99.9])
        for p in [50, 95, 99, 99.9]:
            key = f"P{p}"
            if key in cpu_percentiles:
                print(f"    {key:>6}: {cpu_percentiles[key]:>6} µs")

print("\n" + "=" * 60)
print("Test completed successfully!")
