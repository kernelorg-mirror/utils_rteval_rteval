#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
source tests/e2e/engine.sh
test_begin

set_timeout 2m

# stress-ng checks
rteval_config="[rteval]
duration:  60.0
report_interval: 600

[measurement]

[loads]
stressng:  module
"

check "stress-ng debug" \
    "--onlyload -D -d 1" 0 '\[DEBUG\]'

check "stress-ng command" \
    "--onlyload -D -d 1 --stressng-option procfs --stressng-arg 1" 0 \
    'starting with stress-ng --procfs 1 --taskset'

check "stress-ng command, with --loads-cpulist" \
    "--onlyload -D -d 1 --loads-cpulist=0-2 --stressng-option procfs --stressng-arg 1" 0 \
    'starting with stress-ng --procfs 1 --taskset 0,1,2'

check "stress-ng command, with --stressng-timeout" \
    "--onlyload -D -d 1 --stressng-option procfs --stressng-arg 1 --stressng-timeout 2" 0 \
    'starting with stress-ng --procfs 1 --timeout 2'

# hackbench checks
rteval_config="[rteval]
duration:  60.0
report_interval: 600

[measurement]

[loads]
hackbench:  module
"

check "hackbench command" \
    "--onlyload --hackbench-runlowmem=True -D -d 1" 0 \
    "starting on node 0: args = ['taskset', '-c', '[0-9|,]+', 'hackbench', '-P', '-g', '42', '-l', '1000', '-s', '1000']"

check "hackbench command, with --loads-cpulist" \
    "--onlyload --hackbench-runlowmem=True --loads-cpulist=0-2 -D -d 1" 0 \
    "starting on node 0: args = ['taskset', '-c', '0,1,2', 'hackbench', '-P', '-g', '42', '-l', '1000', '-s', '1000']"

# kcompile checks
rteval_config="[rteval]
duration:  60.0
report_interval: 600

[measurement]

[loads]
kcompile:  module
"

check "kcompile command" \
    "--onlyload -D -d 1" 0 \
    'running on node 0: taskset -c [0-9|,]+ make O=.* -C .* -j[0-9]+'

check "kcompile command, with --loads-cpulist" \
    "--onlyload --loads-cpulist=0-2 -D -d 1" 0 \
    'running on node 0: taskset -c 0,1,2 make O=.* -C .* -j6'

test_end
