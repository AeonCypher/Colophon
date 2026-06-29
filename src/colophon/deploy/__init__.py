"""Deploy package public entry point.

Exports ``deploy_site`` from the pipeline while config, Mastodon, and transport
dataflow remains split across focused deploy modules.
"""

from __future__ import annotations

from .pipeline import deploy_site

__all__ = ["deploy_site"]
