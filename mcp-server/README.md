# rteval MCP Server

An MCP (Model Context Protocol) server for querying and analyzing rteval test results.

## License

SPDX-License-Identifier: GPL-2.0-or-later

Copyright 2026 John Kacur <jkacur@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

## Purpose

This MCP server provides tools to:
- List and discover rteval result files
- Parse rteval XML/JSON output
- Compare multiple test runs
- Query historical performance data
- Analyze latency trends across runs

## Target Users

System administrators, QE engineers, and developers who run rteval regularly for:
- Real-time kernel validation
- Performance regression testing
- CI/CD pipelines
- System certification

## Current Status

**Prototype/Development** - This is a first attempt at building an MCP server for rteval.
The initial focus is on multi-run analysis rather than single-result querying.

## Installation

On Fedora:
```bash
sudo dnf install python3-mcp python3-mcp+cli python3-lxml
```

## Available Tools

### Basic Analysis
- **list_results**: List rteval result files in a directory
- **parse_result**: Parse an rteval XML result file and extract key metrics
- **compare_results**: Compare two rteval result files side-by-side
- **batch_analysis**: Analyze multiple rteval result files and aggregate statistics

### Query & Filter
- **filter_results**: Filter rteval results by kernel version, date range, test duration, and latency thresholds
- **find_best_worst**: Find best and worst rteval runs based on latency metrics (maximum, mean, or median)
- **compare_to_baseline**: Compare multiple results against a baseline file and detect regressions

### Log Access
- **list_logs**: List available log files in an rteval result directory
- **read_log**: Read log content with optional filtering (head/tail/grep)

### Histogram & Per-CPU Analysis
- **extract_histogram**: Extract latency histogram data from rteval results
- **get_percentiles**: Calculate latency percentiles (P50, P95, P99, P99.9, etc.)
- **get_per_cpu_stats**: Get per-CPU latency statistics and identify problematic cores

### Load Analysis
- **get_load_info**: Extract load configuration and metrics from an rteval result file

## Usage

### Testing the Server Directly

```bash
python3 test_tools.py
```

### Using with Claude Code

The server is configured as a Claude Code plugin. After installation:

1. The server is registered in `~/.claude/plugins/installed_plugins.json`
2. Enabled in `~/.claude/settings.json`
3. Restart Claude Code to load the plugin
4. Tools will be available with the prefix: `mcp__rteval-mcp__`

Example queries:
```
list rteval results in ~/src/rteval
find the best and worst rteval runs
show me rteval results with kernel 7.0
compare rteval results to a baseline
```

### Query & Filter Examples

**Find best and worst runs:**
```
Find the 3 best and worst rteval runs by maximum latency
Which rteval runs had the lowest mean latency?
```

**Filter by criteria:**
```
Show me rteval results with kernel version 7.0
Find rteval results from June 2026
Show results with max latency under 3500 microseconds
Filter rteval results by RT kernel
```

**Baseline comparison:**
```
Compare all rteval results to rteval-20260605-1/summary.xml
Check for regressions against the baseline with 5% threshold
```

**Batch analysis:**
```
Analyze all rteval results and show aggregate statistics
What's the average max latency across all runs?
```

**Histogram and percentiles:**
```
Extract histogram data from rteval-20260714-1/summary.xml
Calculate P99 and P99.9 percentiles for rteval-20260714-1/summary.xml
Show me percentiles for each CPU in rteval-20260714-1/summary.xml
What percentage of samples had latency under 10 microseconds?
```

**Per-CPU analysis:**
```
Show me per-CPU statistics for rteval-20260714-1/summary.xml
Which CPUs had the worst maximum latency?
Show the top 5 CPUs sorted by mean latency
Highlight CPUs with max latency above 1000 microseconds
Which CPUs have the most variable latency?
```

### Using with MCP Inspector

```bash
mcp dev server.py
```

## Complete Tool Usage Guide

This section shows both the technical tool call format and natural language queries users can ask.

### list_results

**Tool Call:**
```python
list_results(directory=".", pattern="*.xml")
```

**User Asks:**
- "List all rteval results"
- "Show me rteval result files in ~/src/rteval"
- "What rteval results are in the current directory?"

---

### parse_result

**Tool Call:**
```python
parse_result(file_path="rteval-20260724-1/summary.xml")
```

**User Asks:**
- "Parse rteval-20260724-1"
- "Show me the results from rteval-20260724-1"
- "What's in the rteval-20260724-1 summary?"
- "Analyze rteval-20260724-1/summary.xml"

---

### compare_results

**Tool Call:**
```python
compare_results(file1="rteval-20260724-1/summary.xml",
                file2="rteval-20260724-2/summary.xml")
```

**User Asks:**
- "Compare rteval-20260724-1 and rteval-20260724-2"
- "What's the difference between rteval-20260724-1 and rteval-20260724-2?"
- "Show me a comparison of these two rteval runs"

---

### batch_analysis

**Tool Call:**
```python
batch_analysis(directory=".", pattern="*.xml", recursive=False)
```

**User Asks:**
- "Analyze all rteval results"
- "Show me aggregate statistics for all rteval runs"
- "What's the average max latency across all results?"
- "Summarize all rteval results"
- "What's the range of load averages across all runs?"

---

### filter_results

**Tool Call:**
```python
filter_results(directory=".",
               kernel_pattern="7.0",
               is_rt=True,
               date_from="2026-06-01",
               date_to="2026-07-31",
               min_duration_minutes=5,
               max_latency_threshold=6000,
               load_type="hackbench",
               min_load_average=1000,
               max_load_average=1500)
```

**User Asks:**
- "Show me rteval results with kernel 7.0"
- "Find rteval results from June 2026"
- "Show results with max latency under 6000 microseconds"
- "Filter rteval results by RT kernel"
- "Show me results that used hackbench"
- "Find runs with load average between 1000 and 1500"
- "Which results ran with kcompile load?"
- "Show me RT kernel runs with stress-ng that had low latency"

---

### find_best_worst

**Tool Call:**
```python
find_best_worst(directory=".", metric="maximum", count=5)
```

**User Asks:**
- "Find the 3 best and worst rteval runs by maximum latency"
- "Which rteval runs had the lowest mean latency?"
- "Show me the 5 best and worst runs"
- "What were the top performing runs by median latency?"

---

### compare_to_baseline

**Tool Call:**
```python
compare_to_baseline(baseline_file="rteval-20260605-1/summary.xml",
                    directory=".",
                    threshold_percent=10)
```

**User Asks:**
- "Compare all rteval results to rteval-20260605-1/summary.xml"
- "Check for regressions against the baseline"
- "Which runs regressed compared to rteval-20260605-1?"
- "Are there any performance regressions with 5% threshold?"

---

### list_logs

**Tool Call:**
```python
list_logs(result_dir="rteval-20260724-1")
```

**User Asks:**
- "List logs in rteval-20260724-1"
- "What log files are available for rteval-20260724-1?"
- "Show me the logs from this run"

---

### read_log

**Tool Call:**
```python
read_log(log_path="rteval-20260724-1/logs/timerlat.stdout",
         tail=100,
         grep="error")
```

**User Asks:**
- "Show me the last 100 lines of the timerlat log"
- "Read the timerlat stdout from rteval-20260724-1"
- "Search for 'error' in the timerlat log"
- "Show me the beginning of the kcompile log"

---

### extract_histogram

**Tool Call:**
```python
extract_histogram(file_path="rteval-20260714-1/summary.xml",
                  include_per_cpu=True)
```

**User Asks:**
- "Extract histogram data from rteval-20260714-1"
- "Show me the latency distribution for rteval-20260714-1"
- "What does the histogram look like?"
- "Show me per-CPU histogram data"

---

### get_percentiles

**Tool Call:**
```python
get_percentiles(file_path="rteval-20260714-1/summary.xml",
                percentiles=[50, 90, 95, 99, 99.9, 99.99],
                per_cpu=False)
```

**User Asks:**
- "Calculate P99 and P99.9 percentiles for rteval-20260714-1"
- "Show me percentiles for each CPU in rteval-20260714-1"
- "What percentage of samples had latency under 10 microseconds?"
- "What's the P95 latency?"
- "Show me per-CPU percentiles"

---

### get_per_cpu_stats

**Tool Call:**
```python
get_per_cpu_stats(file_path="rteval-20260714-1/summary.xml",
                  sort_by="maximum",
                  show_top_n=5,
                  highlight_threshold=1000)
```

**User Asks:**
- "Show me per-CPU statistics for rteval-20260714-1"
- "Which CPUs had the worst maximum latency?"
- "Show the top 5 CPUs sorted by mean latency"
- "Highlight CPUs with max latency above 1000 microseconds"
- "Which CPUs have the most variable latency?"
- "Which CPU had the worst latency spike?"

---

### get_load_info

**Tool Call:**
```python
get_load_info(file_path="rteval-20260724-1/summary.xml")
```

**User Asks:**
- "What loads were running in rteval-20260724-1?"
- "Show me the load configuration for rteval-20260724-1"
- "What was the load average in this run?"
- "What load generators were used?"
- "Show me the load setup for this test"

---

## Features in Detail

### filter_results
Filter rteval results by multiple criteria:
- **kernel_pattern**: Match kernel version (e.g., "7.0", "rt", "6.17")
- **is_rt**: Filter by RT kernel (true/false)
- **date_from/date_to**: Date range filter (YYYY-MM-DD format)
- **min_duration_minutes**: Minimum test duration
- **max_latency_threshold**: Maximum acceptable latency in µs
- **load_type**: Filter by load generator type (e.g., "kcompile", "hackbench", "stressng")
- **min_load_average**: Minimum load average threshold
- **max_load_average**: Maximum load average threshold

Examples:
- Find all RT kernel runs from June 2026 with max latency under 4000 µs
- Find runs with hackbench load and load average between 1000 and 1500
- Show runs with stress-ng that had low latency on RT kernels

### find_best_worst
Identify optimal and poorest performing runs:
- **metric**: Choose maximum, mean, or median latency
- **count**: Number of best/worst results to return (default: 5)

Shows ranked results with kernel version, date, and latency metrics.

### compare_to_baseline
Regression detection against a baseline result:
- **baseline_file**: Reference rteval XML file
- **directory**: Directory containing results to compare
- **threshold_percent**: Alert threshold for regressions (default: 10%)

Reports:
- Regressions (results exceeding threshold)
- Passes (results within threshold)
- Detailed percentage changes for all metrics

### batch_analysis
Aggregate statistics across multiple runs:
- Total files analyzed
- Date range coverage
- Min/max/average latencies across all runs
- Min/max/average load averages across all runs
- Individual result summaries with load information

Useful for understanding performance trends over time and correlating load with latency.

### extract_histogram
Extract raw histogram data from rteval results:
- **file_path**: Path to rteval XML result file
- **include_per_cpu**: Include per-CPU histogram data (default: true)

Shows:
- System-wide histogram summary with total samples and latency range
- Top latency values by sample count with percentages
- Per-CPU histogram summaries with individual max latencies

### get_percentiles
Calculate latency percentiles for detailed distribution analysis:
- **file_path**: Path to rteval XML result file
- **percentiles**: List of percentiles to calculate (default: [50, 90, 95, 99, 99.9, 99.99])
- **per_cpu**: Calculate percentiles per CPU (default: false)

Reports:
- System-wide percentiles showing latency distribution
- Per-CPU percentiles when requested for fine-grained analysis

**Why percentiles matter:**
- **Max latency** alone can be misleading (one outlier vs. systematic issues)
- **P99.9** tells you that 99.9% of samples were below this value
- **Percentiles** reveal whether high latencies are rare spikes or regular occurrences
- **Per-CPU percentiles** help identify hardware-specific issues or IRQ affinity problems

Example: If P99.9 = 16µs but max = 1550µs, this tells you the system is excellent with only rare outliers, not a systematic problem.

### get_per_cpu_stats
Get detailed per-CPU latency statistics to identify problematic cores:
- **file_path**: Path to rteval XML result file
- **sort_by**: Metric to sort by - 'maximum', 'mean', 'median', or 'standard_deviation' (default: maximum)
- **show_top_n**: Show only top N worst CPUs (0 = show all, default: 0)
- **highlight_threshold**: Highlight CPUs with max latency above this threshold in µs (optional)

Shows:
- Tabular view of all CPU statistics (samples, min, max, mean, median, standard deviation)
- CPUs sorted by worst performance first for the selected metric
- Warning indicators for CPUs exceeding the threshold
- Summary statistics across all CPUs

**Why per-CPU analysis matters:**
- **Identify problematic cores**: Some CPUs may have significantly worse latency than others
- **Hardware issues**: Bad cores, thermal throttling, or IRQ affinity problems
- **NUMA effects**: CPUs on different sockets may show different behavior
- **CPU pinning**: Determine which CPUs are best for RT workloads

Example use cases:
- "Which CPU had the worst latency spike?" → Sort by maximum
- "Which CPUs are most consistent?" → Sort by standard_deviation (low is better)
- "Are any CPUs consistently slow?" → Sort by mean latency
- "Show me only the 5 worst CPUs" → Use show_top_n=5

## Development

This is a work in progress. The MCP server is being developed in a branch of the
main rteval repository and may be split into a separate repository later.
