#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
source tests/e2e/engine.sh
test_begin

set_timeout 2m

# cyclictest checks
rteval_config="[rteval]
duration:  60.0
report_interval: 600

[measurement]
cyclictest: module

[loads]
"

check "cyclictest debug" \
  "--noload -D -d 1" 0 '\[DEBUG\]'

check "cyclictest duration" \
  "--noload -d 5" 0 "Run duration: 5.0 seconds"

check "cyclictest command, no extra options" \
  "--noload -d 1" 0 'Command: cyclictest -i100 -qmu -h 3500 -p95'

check "cyclictest command, with --measurement-cpulist" \
  "--noload -d 1 --measurement-cpulist=0-1" 0 \
  'Command: cyclictest -i100 -qmu -h 3500 -p95 -t2 -a0-1'

check "cyclictest command, with --measurement-run-on-isolcpus" \
  "--noload -d 1 --measurement-run-on-isolcpus" 0 \
  'Command: cyclictest -i100 -qmu -h 3500 -p95'

check "cyclictest command, with --cyclictest-priority" \
  "--noload -d 1 --cyclictest-priority=80" 0 \
  'Command: cyclictest -i100 -qmu -h 3500 -p80'

check "cyclictest command, with --cyclictest-interval" \
  "--noload -d 1 --cyclictest-interval=1000" 0 \
  'Command: cyclictest -i1000 -qmu -h 3500 -p95'

check "cyclictest command, with --cyclictest-buckets" \
  "--noload -d 1 --cyclictest-buckets=2000" 0 \
  'Command: cyclictest -i100 -qmu -h 2000 -p95'

check "cyclictest command, with --cyclictest-breaktrace" \
  "--noload -d 1 --cyclictest-breaktrace=1" any \
  'Command: cyclictest -i100 -qmu -h 3500 -p95 -t[0-9]+ -a[0-9|-]+ -b1 --tracemark'

check "cyclictest command, with --cyclictest-threshold" \
  "--noload -d 1 --cyclictest-threshold=1" any \
  'Command: cyclictest -i100 -qmu -h 3500 -p95 -t[0-9]+ -a[0-9|-]+ -b1'

# timerlat checks
rteval_config="[rteval]
duration:  60.0
report_interval: 600

[measurement]
timerlat: module

[loads]
"

check "timerlat debug" \
  "--noload -D -d 1" 0 '\[DEBUG\]'

check "timerlat duration" \
  "--noload -d 5" 0 "Run duration: 5.0 seconds"

check "timerlat command, with --measurement-cpulist" \
  "--noload -d 1 --measurement-cpulist=0-1" 0 \
  'Command: rtla timerlat hist -p100 -P f:95 -u -c0-1'

check "timerlat command, with --measurement-run-on-isolcpus" \
  "--noload -d 1 --measurement-run-on-isolcpus" 0 \
  'Command: rtla timerlat hist -p100 -P f:95 -u'

check "timerlat command, with --timerlat-interval" \
  "--noload -d 1 --timerlat-interval 2000" 0 \
  'Command: rtla timerlat hist -p2000 -P f:95'

check "timerlat command, with --timerlat-priority" \
  "--noload -d 1 --timerlat-priority 80" 0 \
  'Command: rtla timerlat hist -p100 -P f:80 -u'

check "timerlat command, with --timerlat-buckets" \
  "--noload -d 1 --timerlat-buckets 4000" 0 \
  'Command: rtla timerlat hist -p100 -P f:95 -u -c[0-9|-]+ -E4000'

check "timerlat command, with --timerlat-stoptrace" \
  "--noload -d 1 --timerlat-stoptrace 1" any \
  'Command: rtla timerlat hist -p100 -P f:95 -u -c[0-9|-]+ -E3500 --no-summary --no-aa --dma-latency=0 -T1'

check "timerlat command, with --timerlat-trace" \
  "--noload -d 1 --timerlat-stoptrace 1 --timerlat-trace trace.txt" any \
  'Command: rtla timerlat hist -p100 -P f:95 -u -c[0-9|-]+ -E3500 --no-summary --no-aa --dma-latency=0 -T1 -t=trace.txt'

test_end
