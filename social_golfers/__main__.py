"""Allow ``python -m social_golfers``."""

import sys

from .cli import main

sys.exit(main())
