from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any

import frontmatter

from colophon import build as build_module
from colophon import cli as cli_module
from colophon import content as content_module
from colophon import expressions as expressions_module
from colophon import images as images_module
from colophon import project as project_module
from colophon.collections import (
    build_collections,
    enrich_post_context,
    sorted_pages,
)
from colophon.build import resolve_required_vendor_assets
from colophon.content import discover_routes, scan_content_tree
from colophon.deploy.config import (
    DEFAULT_DEPLOY_STEPS,
    normalize_deploy_config,
    normalize_deploy_target,
    redact_secrets,
)
from colophon.deploy.mastodon import (
    render_mastodon_post_text,
    select_deploy_post,
    write_source_mastodon_status_url,
)
from colophon.deploy.pipeline import deploy_site as deploy_site_impl
from colophon.deploy.transports import (
    is_safe_remote_purge_path,
    planned_upload_actions,
    upload_site_directory,
)
from colophon.errors import ExpressionResolutionError, ProjectConfigError
from colophon.expressions import (
    YAML_FUNCTIONS,
    import_python_module,
    module_yaml_functions,
    resolve_env_references,
    resolve_site_expressions,
    resolve_yaml_expressions,
)
from colophon.images import (
    Image,
    make_image_resolver as make_image_resolver_impl,
    parse_position,
    smart_crop_position,
)
from colophon.markdown import render_markdown
from colophon.mastodon import (
    DEFAULT_MASTODON_TIMELINE,
    normalize_mastodon_comments,
    normalize_mastodon_site_config,
)
from colophon.models import PageContext, ProjectPaths, Route, SourceFile
from colophon.project import project_from_config
from colophon.scaffold import scaffold_site
from colophon.utils import copy_value, deep_merge
from colophon.vendor import (
    download_vendor_assets,
    expand_vendor_assets,
    missing_vendor_files,
    normalize_vendor_config,
    required_vendor_assets,
    validate_local_vendor_assets,
    vendor_url_for,
)


ROOT = project_module.ROOT
CONTENT = project_module.CONTENT
POSTS = project_module.POSTS
CONTENT_IMAGES = project_module.CONTENT_IMAGES
TEMPLATES = project_module.TEMPLATES
STATIC = project_module.STATIC
OUT = project_module.OUT
DEPLOY_CONFIG = project_module.DEPLOY_CONFIG
SITE_CONFIGS = project_module.SITE_CONFIGS
IMAGE_CONFIGS = project_module.IMAGE_CONFIGS
POST_SIDEBAR_CONFIGS = project_module.POST_SIDEBAR_CONFIGS
WATCHED_DIRS = project_module.WATCHED_DIRS
WATCHED_FILES = project_module.WATCHED_FILES


def test_project() -> ProjectPaths:
    return ProjectPaths(
        root=ROOT,
        content_dir=CONTENT,
        posts_dir=POSTS,
        content_images_dir=CONTENT_IMAGES,
        templates_dir=TEMPLATES,
        static_dir=STATIC,
        output_dir=OUT,
        deploy_config=DEPLOY_CONFIG,
        site_configs=tuple(SITE_CONFIGS),
        image_configs=tuple(IMAGE_CONFIGS),
        post_sidebar_configs=tuple(POST_SIDEBAR_CONFIGS),
        watched_dirs=tuple(WATCHED_DIRS),
        watched_files=tuple(WATCHED_FILES),
        python_modules=(),
    )


def build_site(project: ProjectPaths | None = None) -> None:
    build_module.build_site(test_project() if project is None else project)


def load_site_config(project: ProjectPaths | None = None):
    return content_module.load_site_config(test_project() if project is None else project)


def load_images(project: ProjectPaths | None = None):
    return images_module.load_images(test_project() if project is None else project)


def make_image_resolver(images: dict[str, Any], project: ProjectPaths | None = None):
    return make_image_resolver_impl(images, test_project() if project is None else project)


def expression_registry(project: ProjectPaths | None = None):
    return expressions_module.expression_registry(test_project() if project is None else project)


def deploy_site(project: ProjectPaths | None = None, **kwargs: Any):
    return deploy_site_impl(project=test_project() if project is None else project, **kwargs)


@contextmanager
def patched_project_globals():
    names = [
        "ROOT",
        "CONTENT",
        "POSTS",
        "CONTENT_IMAGES",
        "TEMPLATES",
        "STATIC",
        "OUT",
        "DEPLOY_CONFIG",
        "SITE_CONFIGS",
        "IMAGE_CONFIGS",
        "POST_SIDEBAR_CONFIGS",
        "WATCHED_DIRS",
        "WATCHED_FILES",
    ]
    old = {name: getattr(project_module, name) for name in names}

    try:
        for name in names:
            setattr(project_module, name, globals()[name])
        yield
    finally:
        for name, value in old.items():
            setattr(project_module, name, value)


def main(argv: list[str] | None = None) -> None:
    with patched_project_globals():
        cli_module.main(argv)
