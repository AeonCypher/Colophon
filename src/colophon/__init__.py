"""Public package facade for Colophon.

Imports the curated core API so callers see stable entry points while detailed
dataflow remains in subsystem modules.
"""

from __future__ import annotations

from .core import *  # noqa: F403
