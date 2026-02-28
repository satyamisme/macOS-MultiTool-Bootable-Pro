"""
test_basic.py - Basic functionality tests for logic modules
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import constants
from detection import stub_validator, version_parser

class TestBasics(unittest.TestCase):
    def test_partition_calc_sonoma(self):
        # Sonoma (14.0) ~13GB -> KB
        size_kb = 13 * 1024 * 1024
        size_gb = constants.calculate_partition_size(size_kb, "14.0")
        # With new constants:
        # 13GB + 1.3GB (10% overhead) + 1GB (boot) + 2.2GB (buffer) = 17.5GB
        # Rounded to MB: 13312 + 1331 + 1000 + 2252 = ~17895 MB = 17.89GB
        self.assertGreaterEqual(size_gb, 17000)
        # Previous assertion was in GB, but function returns MB.
        # Let's adjust expectation to match return value (MB) or convert.
        # Wait, calculate_partition_size returns MB.
        # "17896 not less than or equal to 20" implies test expected GB but got MB.

        # Correction: calculate_partition_size returns MB.
        # 18GB = 18432 MB.
        self.assertGreaterEqual(size_gb, 17000)
        self.assertLessEqual(size_gb, 20000)

    def test_partition_calc_sequoia_beta(self):
        # Sequoia (15.0) ~14GB -> KB
        size_kb = 14 * 1024 * 1024
        size_gb = constants.calculate_partition_size(size_kb, "15.0 Beta 2")
        # 14GB + 1.4GB + 1GB + 2.5GB = 18.9GB = 19353 MB
        self.assertGreaterEqual(size_gb, 18000)
        self.assertLessEqual(size_gb, 22000)

    def test_version_parsing(self):
        self.assertEqual(version_parser.parse_version("14.6.1"), (14, 6, 1))
        self.assertEqual(version_parser.parse_version("15.0 Beta 3"), (15, 0, 0))
        self.assertEqual(version_parser.parse_version("10.15.7-RC"), (10, 15, 7))

    def test_version_extraction(self):
        self.assertEqual(constants._extract_version_key("14.6.1"), "14")
        self.assertEqual(constants._extract_version_key("15.2 Beta"), "15")
        self.assertEqual(constants._extract_version_key("10.15.7"), "10.15")

if __name__ == '__main__':
    unittest.main()
