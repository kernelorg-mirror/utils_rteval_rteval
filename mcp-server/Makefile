# SPDX-License-Identifier: GPL-2.0-or-later
#
# Makefile for rteval MCP Server tests
#
# Copyright 2026 John Kacur <jkacur@redhat.com>

PYTHON := python3
TEST_DIR := tests

.PHONY: all help test test-new-tools test-integration test-histogram test-per-cpu clean

all: test

help:
	@echo "rteval MCP Server - Test targets:"
	@echo ""
	@echo "  make                   - Run all tests (default)"
	@echo "  make test              - Run all tests"
	@echo "  make test-new-tools    - Run query/filter tools tests"
	@echo "  make test-integration  - Run MCP integration tests"
	@echo "  make test-histogram    - Run histogram extraction tests"
	@echo "  make test-per-cpu      - Run per-CPU statistics tests"
	@echo "  make clean             - Clean Python cache files"
	@echo ""

test: test-new-tools test-integration test-histogram test-per-cpu
	@echo ""
	@echo "All tests completed successfully"

test-new-tools:
	@echo "Running query/filter tools tests..."
	@cd $(TEST_DIR) && $(PYTHON) test_new_tools.py

test-integration:
	@echo "Running MCP integration tests..."
	@cd $(TEST_DIR) && $(PYTHON) test_mcp_integration.py

test-histogram:
	@echo "Running histogram extraction tests..."
	@cd $(TEST_DIR) && $(PYTHON) test_histogram.py

test-per-cpu:
	@echo "Running per-CPU statistics tests..."
	@cd $(TEST_DIR) && $(PYTHON) test_per_cpu_stats.py

clean:
	@echo "Cleaning Python cache files..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -delete
	@find . -type f -name '*.pyo' -delete
	@echo "Clean completed"
