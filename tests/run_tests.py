#!/usr/bin/env python
"""
run_tests.py - Discover and run all RichBuddy tests using unittest.

Usage:  python tests/run_tests.py
"""

import os
import sys
import unittest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def main():
    loader = unittest.TestLoader()
    # Discover all test files in the tests/ directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(test_dir, pattern="test_*.py", top_level_dir=project_root)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with non-zero code if any tests failed
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
