"""Allow ``python -m sudoku``."""

import sys

from .cli import main

sys.exit(main())
