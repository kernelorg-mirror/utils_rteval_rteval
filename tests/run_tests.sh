#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 John Kacur <jkacur@redhat.com>
#
# Test runner for rteval unit tests
#
# This script runs all unit tests in the tests_progs/ directory
# and provides a summary of results.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Some unit tests (e.g. the DMI sysinfo test) require root privileges,
# which matches how rteval itself is normally run.
if [ "$(id -u)" != "0" ]; then
    echo -e "${RED}ERROR: unit tests must be run as root${NC}"
    echo "Usage: sudo make tests   (or: sudo make unit-tests)"
    exit 1
fi

# Get the directory where this script is located (tests/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Change to repository root (parent of tests/)
cd "$SCRIPT_DIR/.."

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

echo "========================================="
echo "Running rteval Unit Tests"
echo "========================================="
echo ""

# Function to run a single test
run_test() {
    local test_file=$1
    local test_name=$(basename "$test_file" .py)

    echo -e "${YELLOW}Running: ${test_name}${NC}"
    echo "---"

    if python3 "$test_file"; then
        echo -e "${GREEN}✓ PASSED: ${test_name}${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAILED: ${test_name}${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
}

# Find and run all Python test files in tests/
# Discovered dynamically so new test files are picked up automatically:
#   - tests/test_*.py          (unittest-based and script-style tests)
#   - tests/unittest-legacy.py (legacy custom harness, does not match test_*.py)
if [ -d "tests" ]; then
    shopt -s nullglob
    test_files=(tests/test_*.py tests/unittest-legacy.py)
    if [ ${#test_files[@]} -eq 0 ]; then
        echo -e "${RED}Error: no test files found in tests/${NC}"
        exit 1
    fi
    for test_file in "${test_files[@]}"; do
        run_test "$test_file"
    done
else
    echo -e "${RED}Error: tests/ directory not found${NC}"
    exit 1
fi

# Print summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Total tests run: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
else
    echo -e "Failed: $FAILED_TESTS"
fi
echo ""

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
