# -*- coding: utf-8 -*-
"""Game inventory generator.

Usage:  py generate_inventory.py (from the project folder)
Options: --lang en|es, --offline, --keep, --force-purge, --output PATH.
The code lives in the inventory/ package.
"""

from inventory.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
