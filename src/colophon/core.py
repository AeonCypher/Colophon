"""Compatibility facade for stable Colophon entry points.

External callers may import this small surface; implementation dataflow lives in
the build, deploy, project, scaffold, serve, and CLI modules.
"""

from __future__ import annotations

from .build import build_site
from .cli import main
from .deploy.pipeline import deploy_site
from .project import default_config_project, project_from_config
from .scaffold import scaffold_site
from .serve import serve_site

__all__ = [
    "build_site",
    "default_config_project",
    "deploy_site",
    "main",
    "project_from_config",
    "scaffold_site",
    "serve_site",
]


if __name__ == "__main__":
    main()
