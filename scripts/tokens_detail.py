#!/usr/bin/env python3
"""token-report --detail 的入口别名。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from token_report import main

if __name__ == "__main__":
    if "--detail" not in sys.argv:
        sys.argv.insert(1, "--detail")
    main()
