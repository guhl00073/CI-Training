#!/usr/bin/env python3
"""
CI-Hörtrainer (Modern Web UI Edition)
Main Launcher Script
"""

import sys
import os

# Ensure project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.web.server import start_web_server

def main():
    print("==================================================")
    print("   👂 CI-Hörtrainer (Modernes Hörtrainingsprogramm)")
    print("==================================================")
    start_web_server(open_browser=True)

if __name__ == "__main__":
    main()
