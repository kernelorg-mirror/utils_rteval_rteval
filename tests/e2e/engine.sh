#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
load_default_config() {
	rteval_config=$(<$RTEVAL_PKG/rteval.conf)
}

test_begin() {
	# Count tests to allow the test harness to double-check if all were
	# included correctly.
	ctr=0
	[ -z "$PYTHON" ] && PYTHON="python3"
	[ -z "$RTEVAL" ] && RTEVAL="$PWD/rteval-cmd"
	[ -z "$RTEVAL_PKG" ] && RTEVAL_PKG="$PWD"
	[ -n "$TEST_COUNT" ] && echo "1..$TEST_COUNT"
	load_default_config
}

check() {
	test_name=$0
	tested_command=$1
	expected_exitcode=${3:-0}
	expected_output=$4
	grep_flags=$5
	# Simple check: run rteval with given arguments and test exit code.
	# If TEST_COUNT is set, run the test. Otherwise, just count.
	ctr=$(($ctr + 1))
	if [ -n "$TEST_COUNT" ]
	then
		# Create a temporary directory to contain rteval output
		tmpdir=$(mktemp -d)
		pushd $tmpdir >/dev/null
		cat <<< $rteval_config > rteval.conf
		# Run rteval; in case of failure, include its output as comment
		# in the test results.
		result=$(PYTHONPATH="$RTEVAL_PKG" stdbuf -oL $TIMEOUT $PYTHON "$RTEVAL" $2 2>&1); exitcode=$?
		# Test if the results matches if requested
		if [ -n "$expected_output" ]
		then
			grep $grep_flags -E "$expected_output" <<< "$result" > /dev/null; grep_result=$?
		else
			grep_result=0
		fi

		# If expected exitcode is any, allow any exit code
		[ "$expected_exitcode" == "any" ] && expected_exitcode=$exitcode

		if [ $exitcode -eq $expected_exitcode ] && [ $grep_result -eq 0 ]
		then
			echo "ok $ctr - $1"
		else
			echo "not ok $ctr - $1"
			# Add rtla output and exit code as comments in case of failure
			[ -n "$expected_output" ] && [ $grep_result -ne 0 ] && \
				printf "# Output match failed: \"%s\"\n" "$expected_output"
			echo "$result" | col -b | while read line; do echo "# $line"; done
			printf "#\n# exit code %s\n" $exitcode
		fi

		# Remove temporary directory
		popd >/dev/null
		rm -r $tmpdir
	fi
}

set_timeout() {
	TIMEOUT="timeout -v -k 15s $1"
}

unset_timeout() {
	unset TIMEOUT
}

test_end() {
	# If running without TEST_COUNT, tests are not actually run, just
	# counted. In that case, re-run the test with the correct count.
	[ -z "$TEST_COUNT" ] && TEST_COUNT=$ctr exec bash $0 || true
}

# Avoid any environmental discrepancies
export LC_ALL=C
unset_timeout
