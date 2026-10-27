#!/usr/bin/env python3
"""
Entrypoint for IIST RPM Desktop Scientific Workstation v2.0.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from desktop.rpm_workstation import main

if __name__ == "__main__":
    main()
