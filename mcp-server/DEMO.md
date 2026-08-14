# rteval MCP Server Demo Guide

This document provides example queries to demonstrate the capabilities of the rteval MCP server when used with Claude Code.

## License

SPDX-License-Identifier: GPL-2.0-or-later

Copyright 2026 John Kacur <jkacur@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

## Prerequisites

Before running the demo, ensure you have rteval result files available:

```bash
# Generate some test data if needed
cd ~/src/rteval
sudo ./rteval-cmd --duration=5m

# Or use existing results in the rteval directory
ls -d rteval-*/
```

## Basic Operations

### Discovering Results

**Query:** "List all rteval results in the current directory"

**Expected:** Shows all rteval-YYYYMMDD-N directories with summary.xml files

---

**Query:** "What rteval results are available?"

**Expected:** Same as above - lists available result directories

---

### Parsing Individual Results

**Query:** "Parse the latest rteval result"

**Expected:** Shows comprehensive summary including:
- System info (kernel version, architecture, CPU count)
- Test duration and date
- Maximum, mean, and median latency
- Load information

---

**Query:** "Show me the results from rteval-20260714-1"

**Expected:** Detailed metrics for that specific run

---

### Comparing Two Results

**Query:** "Compare rteval-20260714-1 and rteval-20260715-1"

**Expected:** Side-by-side comparison showing:
- Kernel versions
- Latency differences (max, mean, median)
- Load configuration differences
- Performance improvement/regression percentages

---

## Query and Filtering

### Kernel-Based Filtering

**Query:** "Show me rteval results with kernel 7.0"

**Expected:** Filtered list showing only results running kernel 7.0.x

---

**Query:** "Find rteval results running RT kernels"

**Expected:** Results filtered to show only RT (PREEMPT_RT) kernels

---

### Date Range Filtering

**Query:** "Show me rteval results from June 2026"

**Expected:** Results filtered by date range

---

**Query:** "Find rteval results from the last week"

**Expected:** Recent results within the specified timeframe

---

### Latency Threshold Filtering

**Query:** "Show results with max latency under 5000 microseconds"

**Expected:** Only results where maximum latency is below the threshold

---

**Query:** "Find rteval runs with excellent latency (max < 3000 µs)"

**Expected:** High-performing results meeting the latency criteria

---

### Load Generator Filtering

**Query:** "Show me results that used hackbench"

**Expected:** Results filtered by load generator type

---

**Query:** "Find runs with kcompile load and high load average"

**Expected:** Results using kcompile with specified load characteristics

---

## Best/Worst Analysis

### Finding Best Runs

**Query:** "Find the 5 best rteval runs by maximum latency"

**Expected:** Top 5 runs ranked by lowest maximum latency

---

**Query:** "Which rteval runs had the lowest mean latency?"

**Expected:** Ranked list showing best average performance

---

**Query:** "Show me the best runs by median latency"

**Expected:** Rankings based on median latency metric

---

### Finding Worst Runs

**Query:** "Find the 3 worst rteval runs"

**Expected:** Shows the runs with highest maximum latency

---

**Query:** "Which runs had the poorest performance?"

**Expected:** Identifies problematic runs with high latencies

---

## Histogram and Percentile Analysis

### Extracting Histogram Data

**Query:** "Extract histogram data from rteval-20260714-1"

**Expected:** Shows:
- Total sample count
- Latency range (min to max)
- Top latency buckets with counts and percentages
- Per-CPU histogram summaries

---

**Query:** "Show me the latency distribution for the latest rteval run"

**Expected:** Histogram showing how latency values are distributed

---

### Percentile Calculations

**Query:** "Calculate P99 and P99.9 percentiles for rteval-20260714-1"

**Expected:** Shows percentile values like:
- P50 (median)
- P90
- P95
- P99
- P99.9
- P99.99

---

**Query:** "What's the P95 latency for the latest run?"

**Expected:** Specific percentile value showing that 95% of samples were below this latency

---

**Query:** "Show me per-CPU percentiles for rteval-20260714-1"

**Expected:** Percentile breakdown for each individual CPU

---

**Query:** "What percentage of samples had latency under 10 microseconds?"

**Expected:** Uses histogram to calculate the cumulative percentage

---

## Per-CPU Analysis

### Basic Per-CPU Statistics

**Query:** "Show me per-CPU statistics for rteval-20260714-1"

**Expected:** Table showing for each CPU:
- Sample count
- Min, max, mean, median latency
- Standard deviation

---

**Query:** "Which CPUs had the worst maximum latency?"

**Expected:** CPUs sorted by maximum latency (worst first)

---

### Identifying Problem CPUs

**Query:** "Show the top 5 CPUs sorted by mean latency"

**Expected:** Table limited to 5 worst CPUs by average latency

---

**Query:** "Highlight CPUs with max latency above 5000 microseconds"

**Expected:** Table with ⚠️ warning symbols next to CPUs exceeding threshold

---

**Query:** "Which CPUs have the most variable latency?"

**Expected:** CPUs sorted by standard deviation (highest first)

---

**Query:** "Which CPU had the worst latency spike?"

**Expected:** Single CPU with the absolute highest maximum latency

---

### Consistency Analysis

**Query:** "Show me the most consistent CPUs"

**Expected:** CPUs sorted by standard deviation (lowest first = most consistent)

---

**Query:** "Are any CPUs consistently slow?"

**Expected:** Analysis of mean latency to find systematically poor performers

---

## Load Analysis

### Load Configuration

**Query:** "What loads were running in rteval-20260714-1?"

**Expected:** Shows:
- Load generator types (hackbench, kcompile, stressng)
- Load configuration parameters
- Load average (1-min, 5-min, 15-min)

---

**Query:** "Show me the load setup for the latest test"

**Expected:** Complete load configuration and metrics

---

**Query:** "What was the load average in this run?"

**Expected:** System load averages during the test

---

## Batch Analysis

### Aggregate Statistics

**Query:** "Analyze all rteval results"

**Expected:** Aggregate statistics showing:
- Total files analyzed
- Date range coverage
- Min/max/average latencies across all runs
- Min/max/average load averages
- Individual result summaries

---

**Query:** "What's the average max latency across all runs?"

**Expected:** Single aggregate metric across all results

---

**Query:** "Show me the range of load averages across all runs"

**Expected:** Min and max load averages from all results

---

### Baseline Comparison

**Query:** "Compare all rteval results to rteval-20260605-1/summary.xml"

**Expected:** Shows:
- Baseline metrics
- Regressions (results exceeding threshold)
- Passes (results within threshold)
- Detailed percentage changes for all comparisons

---

**Query:** "Check for regressions against the baseline with 5% threshold"

**Expected:** Regression detection with custom threshold

---

**Query:** "Which runs regressed compared to rteval-20260605-1?"

**Expected:** List of runs that performed worse than baseline

---

## Log Analysis

### Listing Logs

**Query:** "List logs in rteval-20260714-1"

**Expected:** Shows available log files:
- timerlat.stdout
- hackbench.stdout
- kcompile.stdout
- dmesg
- etc.

---

**Query:** "What log files are available for the latest run?"

**Expected:** Complete list of log files in the result directory

---

### Reading Logs

**Query:** "Show me the last 100 lines of the timerlat log"

**Expected:** Tail of the timerlat stdout log

---

**Query:** "Search for 'error' in the timerlat log"

**Expected:** Filtered log showing only lines containing 'error'

---

**Query:** "Show me the beginning of the kcompile log"

**Expected:** First lines (head) of the kcompile log

---

## Advanced Queries

### Multi-Criteria Filtering

**Query:** "Show me RT kernel runs from June 2026 with max latency under 4000 µs"

**Expected:** Results matching all three criteria:
- RT kernel
- Date in June 2026
- Max latency < 4000 µs

---

**Query:** "Find runs with hackbench load and load average between 1000 and 1500"

**Expected:** Results filtered by load type and load average range

---

### Comparative Analysis

**Query:** "How does kernel 7.0 compare to kernel 6.17 in terms of latency?"

**Expected:** Filtering and comparison showing performance differences between kernel versions

---

**Query:** "Show the latency trend over time"

**Expected:** Batch analysis ordered by date showing temporal patterns

---

## Tips for Effective Queries

1. **Be specific with file paths:** Use actual rteval directory names from your system
2. **Combine criteria:** Most tools support multiple filters for precise analysis
3. **Use natural language:** The MCP server understands conversational queries
4. **Ask follow-ups:** Build on previous queries to dive deeper into results
5. **Verify thresholds:** When filtering by latency, make sure thresholds match your RT requirements

## Expected Data Requirements

For the best demo experience, have:
- At least 5-10 rteval result directories
- Results from different kernel versions (preferably mix of RT and non-RT)
- Results spanning different dates
- Variety of load generators (hackbench, kcompile, stressng)
- Some high-latency and some low-latency results for comparison

## Troubleshooting Demo Issues

If queries don't work as expected:

1. **No results found:** Check that rteval result directories exist with summary.xml files
2. **Empty filters:** Adjust filter criteria to match your actual test data
3. **Tool not found:** Verify the MCP server is properly installed and enabled in Claude Code
4. **Permission errors:** Ensure rteval results are readable by your user

## Next Steps

After completing the demo:
- Review the full tool documentation in README.md
- Run `make test` to verify the MCP server installation
- Create baseline results for your specific RT requirements
- Set up automated regression testing using the baseline comparison tools
