"""
Root Runner: Fast Manhwa & Comic Compression Tool
Run directly from terminal:
    python compress.py "path/to/manhwa_folder" -o output.cbz
"""

import sys
import os

# Ensure current directory is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cli import main

if __name__ == "__main__":
    main()

