"""Python version compatibility helpers."""

from __future__ import annotations

import sys
from enum import Enum

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:

    class StrEnum(str, Enum):
        """Backport of enum.StrEnum for Python 3.10."""
