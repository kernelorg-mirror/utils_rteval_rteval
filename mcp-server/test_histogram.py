#!/usr/bin/env python3
"""
Test script for histogram extraction and percentile calculation.
"""

from server import extract_histogram_data, calculate_percentiles

# Test with the sample file
test_file = "../rteval-20260714-1/summary.xml"

print("Testing histogram extraction...")
print("=" * 60)

# Extract histogram data
histogram_data = extract_histogram_data(test_file)

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
