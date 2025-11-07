#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
source tests/e2e/engine.sh
test_begin

set_timeout 2m

check "help message" \
  "--help" 0 "usage: rteval-cmd"

check "help message short" \
  "-h" 0 "usage: rteval-cmd"

check "debug" \
  "-D -d 1" 0 '\[DEBUG\]'

check "duration" \
  "-d 5" 0 "Run duration: 5.0 seconds"

check "verbose" \
  "-v -d 5" 0 '\[INFO\]'

check "quiet" \
  "-d 5" 0 '(\[INFO\])|(\[DEBUG\])' "-v"

test_end
