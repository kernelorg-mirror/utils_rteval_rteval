#!/usr/bin/env python3
"""
Mock cyclictest that produces partial/malformed histogram output
to test rteval's error handling improvements (RHEL-140898)

This simulates the output that cyclictest might produce when:
1. It segfaults mid-execution (partial histogram)
2. Gets killed during cleanup (incomplete lines)
3. Has data corruption (malformed values)
"""

import sys
import signal
import time
import random

# Track if we should exit
should_exit = False

def handle_sigint(sig, frame):
    global should_exit
    print("# Received SIGINT, cleaning up...", file=sys.stderr)
    should_exit = True

signal.signal(signal.SIGINT, handle_sigint)

def print_histogram_header():
    """Print the standard cyclictest histogram header"""
    print("# /dev/cpu_dma_latency set to 0us")
    print("# Histogram")
    print("#")

def print_partial_histogram(scenario="truncated_mid_line", num_cpus=4):
    """
    Print histogram data with various types of corruption

    Scenarios:
    - truncated_mid_line: Line cuts off mid-way (IndexError)
    - missing_columns: Missing some CPU columns (IndexError)
    - invalid_numbers: Non-numeric values (ValueError)
    - mixed_corruption: Combination of issues
    """

    # Print max latencies header (can also be corrupted)
    if scenario == "missing_columns" and random.random() < 0.5:
        # Truncated max latencies line
        print(f"# Max Latencies: {random.randint(10,100)} {random.randint(10,100)}")
    else:
        max_vals = " ".join([str(random.randint(10, 100)) for _ in range(num_cpus)])
        print(f"# Max Latencies: {max_vals}")

    if scenario == "truncated_mid_line":
        # Normal lines first
        for i in range(10):
            vals = " ".join([f"{random.randint(0,100):10d}" for _ in range(num_cpus)])
            print(f"{i:10d} {vals}")

        # Then a truncated line (simulates segfault mid-write)
        vals = " ".join([f"{random.randint(0,100):10d}" for _ in range(2)])  # Only 2 of 4 CPUs
        print(f"{10:10d} {vals}")
        # Output ends abruptly here

    elif scenario == "missing_columns":
        # Some lines missing data for certain CPUs
        for i in range(20):
            if i % 5 == 0:
                # Missing last two CPUs
                vals = " ".join([f"{random.randint(0,100):10d}" for _ in range(2)])
                print(f"{i:10d} {vals}")
            elif i % 3 == 0:
                # Missing last CPU
                vals = " ".join([f"{random.randint(0,100):10d}" for _ in range(3)])
                print(f"{i:10d} {vals}")
            else:
                # Normal line
                vals = " ".join([f"{random.randint(0,100):10d}" for _ in range(num_cpus)])
                print(f"{i:10d} {vals}")

    elif scenario == "invalid_numbers":
        # Lines with non-numeric values
        for i in range(15):
            if i % 4 == 0:
                # Corrupted data - one CPU has invalid value
                vals = [f"{random.randint(0,100):10d}" for _ in range(num_cpus)]
                vals[random.randint(0, num_cpus-1)] = "XXXX      "  # Replace one with garbage
                print(f"{i:10d} {' '.join(vals)}")
            else:
                # Normal line
                vals = " ".join([f"{random.randint(0,100):10d}" for _ in range(num_cpus)])
                print(f"{i:10d} {vals}")

    elif scenario == "mixed_corruption":
        # Combination of issues
        for i in range(20):
            rand = random.random()
            if rand < 0.2:
                # Truncated
                num_cols = random.randint(1, num_cpus-1)
                vals = " ".join([f"{random.randint(0,100):10d}" for _ in range(num_cols)])
                print(f"{i:10d} {vals}")
            elif rand < 0.4:
                # Invalid data
                vals = [f"{random.randint(0,100):10d}" for _ in range(num_cpus)]
                vals[random.randint(0, num_cpus-1)] = "ERR       "
                print(f"{i:10d} {' '.join(vals)}")
            elif rand < 0.6:
                # Missing column
                num_cols = random.randint(1, num_cpus-1)
                vals = " ".join([f"{random.randint(0,100):10d}" for _ in range(num_cols)])
                print(f"{i:10d} {vals}")
            else:
                # Normal
                vals = " ".join([f"{random.randint(0,100):10d}" for _ in range(num_cpus)])
                print(f"{i:10d} {vals}")

def main():
    """Main function to simulate cyclictest with partial output"""

    # Parse scenario from arguments
    scenario = "truncated_mid_line"
    num_cpus = 4

    if len(sys.argv) > 1:
        valid_scenarios = ["truncated_mid_line", "missing_columns", "invalid_numbers", "mixed_corruption"]
        for arg in sys.argv[1:]:
            if arg.startswith("--scenario="):
                requested = arg.split("=")[1]
                if requested in valid_scenarios:
                    scenario = requested
            elif arg.startswith("-t"):
                # Parse thread count (number of CPUs)
                try:
                    num_cpus = int(arg[2:])
                except ValueError:
                    pass

    print(f"# Mock cyclictest starting (scenario: {scenario})", file=sys.stderr)

    # Print header
    print_histogram_header()

    # Simulate some runtime before producing output
    start_time = time.time()
    while not should_exit and (time.time() - start_time) < 5:
        time.sleep(0.1)

    if should_exit:
        print("# Interrupted by SIGINT", file=sys.stderr)

    # Print partial/corrupted histogram
    print_partial_histogram(scenario, num_cpus)

    # Exit (possibly before completing all output)
    print(f"# Mock cyclictest exiting (scenario: {scenario})", file=sys.stderr)

    # Simulate different exit codes
    if scenario == "truncated_mid_line":
        sys.exit(139)  # Segfault exit code
    elif scenario in ["missing_columns", "invalid_numbers"]:
        sys.exit(1)   # Generic error
    else:
        sys.exit(0)   # Normal exit despite bad data

if __name__ == "__main__":
    main()
