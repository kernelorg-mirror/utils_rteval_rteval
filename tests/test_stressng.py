#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2026 Sana Sharma <sansshar@redhat.com>
""" Unit tests for the new stressng input validation """

import sys
import subprocess
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,'.')
from rteval.modules.loads import stressng

class TestGetValidStressors(unittest.TestCase):
    """Test suite for the function get_valid_stressors"""

    @patch('rteval.modules.loads.stressng.subprocess.run')
    def test_parses_stressor_list(self, mock_run):
        """Tests that the function works for multiple correct inputs"""
        mock_run.return_value = MagicMock(stdout="cpu vm matrix\n")
        self.assertEqual(stressng.get_valid_stressors(), ['cpu', 'vm', 'matrix'])

    @patch('rteval.modules.loads.stressng.subprocess.run',
           side_effect=FileNotFoundError)
    def test_not_installed_exits(self, _):
        """Tests that the program exits correctly if stress-ng is not installed"""
        with self.assertRaises(SystemExit) as cm:
            stressng.get_valid_stressors()
        self.assertEqual(cm.exception.code, 1)

    @patch('rteval.modules.loads.stressng.subprocess.run',
           side_effect=subprocess.CalledProcessError(1, 'stress-ng'))
    def test_query_failure_exits(self, _):
        """Tests that the program exits correctly if the query attempt fails"""
        with self.assertRaises(SystemExit):
            stressng.get_valid_stressors()

class TestValidateStressor(unittest.TestCase):
    """Test suite for the function validate_stressor"""

    @patch('rteval.modules.loads.stressng.get_valid_stressors',
           return_value=['cpu', 'vm'])
    def test_valid_passes(self, _):
        """Tests that the function works for correct inputs"""
        stressng.validate_stressor('cpu')   # should not raise

    @patch('rteval.modules.loads.stressng.get_valid_stressors',
           return_value=['cpu', 'vm'])
    def test_invalid_exits(self, _):
        """Tests that the function exits properly for incorrect inputs"""
        with self.assertRaises(SystemExit) as cm:
            stressng.validate_stressor('bogus')
        self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
    unittest.main()
