#!/usr/bin/env python3
"""
Mock rtla timerlat that produces partial/malformed histogram output
to test rteval's error handling improvements (RHEL-140898)

This simulates the output that rtla might produce when:
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
    """Print the standard rtla timerlat histogram header"""
    print("# RTLA timerlat histogram")
    print("# Time unit is microseconds (us)")
    print("# Duration:   0 00:00:30")
    print()

def print_partial_histogram(scenario="truncated_mid_line"):
    """
    Print histogram data with various types of corruption

    Scenarios:
    - truncated_mid_line: Line cuts off mid-way (IndexError)
    - missing_columns: Missing some CPU columns (IndexError)
    - invalid_numbers: Non-numeric values (ValueError)
    - mixed_corruption: Combination of issues
    """

    print("Index   CPU-000        CPU-001        CPU-002        CPU-003")

    if scenario == "truncated_mid_line":
        # Normal lines first
        for i in range(10):
            print(f"{i:5d}   {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d}")

        # Then a truncated line (simulates segfault mid-write)
        print(f"{10:5d}   {random.randint(0,100):10d} {random.randint(0,100):10d}")
        # Output ends abruptly here

    elif scenario == "missing_columns":
        # Some lines missing data for certain CPUs
        for i in range(20):
            if i % 5 == 0:
                # Missing last two CPUs
                print(f"{i:5d}   {random.randint(0,100):10d} {random.randint(0,100):10d}")
            elif i % 3 == 0:
                # Missing last CPU
                print(f"{i:5d}   {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d}")
            else:
                # Normal line
                print(f"{i:5d}   {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d}")

    elif scenario == "invalid_numbers":
        # Lines with non-numeric values
        for i in range(15):
            if i % 4 == 0:
                # Corrupted data
                print(f"{i:5d}   {'XXXX':>10s} {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d}")
            else:
                # Normal line
                print(f"{i:5d}   {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d}")

    elif scenario == "mixed_corruption":
        # Combination of issues
        for i in range(20):
            rand = random.random()
            if rand < 0.2:
                # Truncated
                print(f"{i:5d}   {random.randint(0,100):10d}")
            elif rand < 0.4:
                # Invalid data
                print(f"{i:5d}   {random.randint(0,100):10d} {'ERR':>10s} {random.randint(0,100):10d} {random.randint(0,100):10d}")
            elif rand < 0.6:
                # Missing column
                print(f"{i:5d}   {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d}")
            else:
                # Normal
                print(f"{i:5d}   {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d} {random.randint(0,100):10d}")

def main():
    """Main function to simulate rtla timerlat with partial output"""

    # Parse scenario from arguments
    scenario = "truncated_mid_line"
    if len(sys.argv) > 1:
        valid_scenarios = ["truncated_mid_line", "missing_columns", "invalid_numbers", "mixed_corruption"]
        for arg in sys.argv[1:]:
            if arg.startswith("--scenario="):
                requested = arg.split("=")[1]
                if requested in valid_scenarios:
                    scenario = requested
                    break

    print(f"# Mock rtla starting (scenario: {scenario})", file=sys.stderr)

    # Print header
    print_histogram_header()

    # Simulate some runtime before producing output
    start_time = time.time()
    while not should_exit and (time.time() - start_time) < 5:
        time.sleep(0.1)

    if should_exit:
        print("# Interrupted by SIGINT", file=sys.stderr)

    # Print partial/corrupted histogram
    print_partial_histogram(scenario)

    # Exit (possibly before completing all output)
    print(f"# Mock rtla exiting (scenario: {scenario})", file=sys.stderr)

    # Simulate different exit codes
    if scenario == "truncated_mid_line":
        sys.exit(139)  # Segfault exit code
    elif scenario in ["missing_columns", "invalid_numbers"]:
        sys.exit(1)   # Generic error
    else:
        sys.exit(0)   # Normal exit despite bad data

if __name__ == "__main__":
    main()
