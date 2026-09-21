#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 John Kacur <jkacur@redhat.com>
"""Test script for the new CpuList class"""

import sys
sys.path.insert(0, '.')

from rteval.cpulist_utils import CpuList, expand_cpulist, collapse_cpulist

def test_basic_creation():
    """Test basic CpuList creation"""
    print("=" * 60)
    print("Test 1: Basic Creation")
    print("=" * 60)

    # Create from string
    cpus1 = CpuList("0-7,9-11")
    print(f"CpuList('0-7,9-11') = {cpus1}")
    print(f"  cpus: {cpus1.cpus}")
    print(f"  len: {len(cpus1)}")

    # Create from list
    cpus2 = CpuList([0, 1, 2, 3, 7, 8, 9])
    print(f"\nCpuList([0,1,2,3,7,8,9]) = {cpus2}")
    print(f"  cpus: {cpus2.cpus}")

    print()

def test_operators():
    """Test CpuList operators"""
    print("=" * 60)
    print("Test 2: Operators")
    print("=" * 60)

    cpus = CpuList("0-7")

    # __contains__
    print(f"cpus = {cpus}")
    print(f"  3 in cpus: {3 in cpus}")
    print(f"  10 in cpus: {10 in cpus}")

    # __iter__
    print(f"  Iteration: ", end="")
    for cpu in cpus:
        print(cpu, end=" ")
    print()

    # __eq__
    cpus2 = CpuList([0, 1, 2, 3, 4, 5, 6, 7])
    print(f"  cpus == CpuList([0-7]): {cpus == cpus2}")

    print()

def test_chaining():
    """Test method chaining (requires system with online/isolated info)"""
    print("=" * 60)
    print("Test 3: Method Chaining (filtering won't occur on systems without online/isolated CPU support)")
    print("=" * 60)

    cpus = CpuList("0-15")
    print(f"Original: {cpus}")
    print(f"  CPU count: {len(cpus)}")

    try:
        online = cpus.online()
        print(f"Online: {online}")
        print(f"  CPU count: {len(online)}")

        nonisolated = cpus.online().nonisolated()
        print(f"Online + Non-isolated: {nonisolated}")
        print(f"  CPU count: {len(nonisolated)}")
    except Exception as e:
        print(f"  (Skipped: {e})")

    print()

def test_backward_compatibility():
    """Test that module-level functions still work"""
    print("=" * 60)
    print("Test 4: Backward Compatibility")
    print("=" * 60)

    # Old style - module functions
    expanded = expand_cpulist("0-3,7-9")
    print(f"expand_cpulist('0-3,7-9') = {expanded}")

    collapsed = collapse_cpulist([0, 1, 2, 3, 7, 8, 9])
    print(f"collapse_cpulist([0,1,2,3,7,8,9]) = {collapsed}")

    # New style - static methods
    expanded2 = CpuList.expand("0-3,7-9")
    print(f"CpuList.expand('0-3,7-9') = {expanded2}")

    collapsed2 = CpuList.collapse([0, 1, 2, 3, 7, 8, 9])
    print(f"CpuList.collapse([0,1,2,3,7,8,9]) = {collapsed2}")

    print()

def test_repr():
    """Test repr"""
    print("=" * 60)
    print("Test 5: Repr")
    print("=" * 60)

    cpus = CpuList("0-3,7-9")
    print(f"repr: {repr(cpus)}")
    print(f"str:  {str(cpus)}")

    print()

def test_intersection():
    """Test CpuList.intersection()"""
    print("=" * 60)
    print("Test 6: Intersection")
    print("=" * 60)

    a = CpuList("0-7")

    # Overlap with another CpuList
    result = a.intersection(CpuList("4-11"))
    print(f"CpuList('0-7').intersection(CpuList('4-11')) = {result}")
    assert result == CpuList("4-7"), result
    assert isinstance(result, CpuList)

    # Overlap with a plain list
    result = a.intersection([4, 5, 6, 7, 20])
    print(f"CpuList('0-7').intersection([4,5,6,7,20]) = {result}")
    assert result == CpuList([4, 5, 6, 7]), result

    # Disjoint -> empty
    result = a.intersection(CpuList("8-11"))
    print(f"CpuList('0-7').intersection(CpuList('8-11')) = {result} (len {len(result)})")
    assert len(result) == 0

    # Original is unchanged
    assert a == CpuList("0-7")

    print()

def test_difference():
    """Test CpuList.difference()"""
    print("=" * 60)
    print("Test 7: Difference")
    print("=" * 60)

    a = CpuList("0-7")

    # Difference with another CpuList
    result = a.difference(CpuList("4-11"))
    print(f"CpuList('0-7').difference(CpuList('4-11')) = {result}")
    assert result == CpuList("0-3"), result
    assert isinstance(result, CpuList)

    # Difference with a plain list
    result = a.difference([0, 1])
    print(f"CpuList('0-7').difference([0,1]) = {result}")
    assert result == CpuList("2-7"), result

    # Difference with a superset -> empty
    result = a.difference(CpuList("0-15"))
    print(f"CpuList('0-7').difference(CpuList('0-15')) = {result} (len {len(result)})")
    assert len(result) == 0

    # Original is unchanged
    assert a == CpuList("0-7")

    print()

if __name__ == '__main__':
    print("\nTesting CpuList class implementation\n")

    test_basic_creation()
    test_operators()
    test_chaining()
    test_backward_compatibility()
    test_repr()
    test_intersection()
    test_difference()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
