#!/usr/bin/env python3
"""The plugin's entry point: `scan [--json]` and `cleanup [--json]`, with the bundled `mishlat`
package next to this file. Pure Python: no GTK, no desktop integration."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mishlat.cli import main  # noqa: E402

sys.exit(main(sys.argv))
