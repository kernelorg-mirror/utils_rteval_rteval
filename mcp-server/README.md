# rteval MCP Server

An MCP (Model Context Protocol) server for querying and analyzing rteval test results.

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
4. Tools will be available with the prefix: `mcp__plugin_rteval-mcp_rteval__`

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

## Features in Detail

### filter_results
Filter rteval results by multiple criteria:
- **kernel_pattern**: Match kernel version (e.g., "7.0", "rt", "6.17")
- **is_rt**: Filter by RT kernel (true/false)
- **date_from/date_to**: Date range filter (YYYY-MM-DD format)
- **min_duration_minutes**: Minimum test duration
- **max_latency_threshold**: Maximum acceptable latency in µs

Example: Find all RT kernel runs from June 2026 with max latency under 4000 µs

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
- Individual result summaries

Useful for understanding performance trends over time.

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
