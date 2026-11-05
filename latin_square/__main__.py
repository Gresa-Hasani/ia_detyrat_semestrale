"""Allow ``python -m latin_square``."""

import sys

from .cli import main

sys.exit(main())
