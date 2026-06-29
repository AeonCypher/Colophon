"""Project configuration and path resolution.

Project config flows from ``colophon.yml`` into a ``ProjectPaths`` value that
downstream build, serve, scaffold, and deploy stages consume explicitly.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import ProjectConfigError
from .models import ProjectPaths
from .utils import deep_merge, mapping_value, read_yaml
from .vendor import normalize_vendor_config


ROOT = Path(__file__).resolve().parent


CONTENT = ROOT / "content"


POSTS = CONTENT / "posts"


CONTENT_IMAGES = CONTENT / "images"


TEMPLATES = ROOT / "templates"


STATIC = ROOT / "static"


OUT = ROOT / "_site"


DEPLOY_CONFIG = CONTENT / "deploy.yaml"


SITE_CONFIGS = [CONTENT / "site.yaml", CONTENT / "site.yml"]


IMAGE_CONFIGS = [CONTENT / "images.yaml", CONTENT / "images.yml"]


POST_SIDEBAR_CONFIGS = [CONTENT / "post-sidebar.yaml", CONTENT / "post-sidebar.yml"]


WATCHED_DIRS = [CONTENT, TEMPLATES, STATIC]


WATCHED_FILES = [Path(__file__).resolve()]


DEFAULT_CONFIG_FILE = "colophon.yml"


CONFIG_EXTS = (".yaml", ".yml")


def absolute_project_path(root: Path, value: Any, default: str) -> Path:
    path = Path(str(value or default)).expanduser()
    return path if path.is_absolute() else root / path


def conventional_project(root: Path) -> ProjectPaths:
    root = root.resolve()
    content = root / "content"
    templates = root / "templates"
    static = root / "static"
    output = root / "_site"

    return ProjectPaths(
        root=root,
        content_dir=content,
        posts_dir=content / "posts",
        content_images_dir=content / "images",
        templates_dir=templates,
        static_dir=static,
        output_dir=output,
        deploy_config=content / "deploy.yaml",
        site_configs=(content / "site.yaml", content / "site.yml"),
        image_configs=(content / "images.yaml", content / "images.yml"),
        post_sidebar_configs=(content / "post-sidebar.yaml", content / "post-sidebar.yml"),
        watched_dirs=(content, templates, static),
        watched_files=(),
        python_modules=(),
    )


def legacy_project() -> ProjectPaths:
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


def project_or_default(project: ProjectPaths | None = None) -> ProjectPaths:
    return legacy_project() if project is None else project


def load_project_file(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise ProjectConfigError(f"missing project config: {config_path}")

    data = read_yaml(config_path)
    if not isinstance(data, Mapping):
        raise ProjectConfigError(f"project config must be a YAML mapping: {config_path}")

    return dict(data)


def project_from_config(
    config_path: Path | str = DEFAULT_CONFIG_FILE,
    *,
    content: str | None = None,
    templates: str | None = None,
    static: str | None = None,
    output: str | None = None,
) -> ProjectPaths:
    config_file = Path(config_path).expanduser()
    if not config_file.is_absolute():
        config_file = Path.cwd() / config_file

    root = config_file.parent.resolve()
    raw = load_project_file(config_file)
    raw_paths = mapping_value(raw.get("paths") or raw.get("project"))
    raw_python = mapping_value(raw.get("python"))
    path_values = deep_merge(
        raw_paths,
        {
            key: value
            for key, value in {
                "content": content,
                "templates": templates,
                "static": static,
                "output": output,
            }.items()
            if value is not None
        },
    )
    content_dir = absolute_project_path(root, path_values.get("content"), "content")
    templates_dir = absolute_project_path(root, path_values.get("templates"), "templates")
    static_dir = absolute_project_path(root, path_values.get("static"), "static")
    output_dir = absolute_project_path(root, path_values.get("output"), "_site")
    deploy_config = absolute_project_path(
        root,
        path_values.get("deploy") or path_values.get("deploy_config"),
        "content/deploy.yaml",
    )
    raw_modules = raw_python.get("modules") or []
    module_entries = raw_modules if isinstance(raw_modules, list) else [raw_modules]
    python_modules = tuple(
        absolute_project_path(root, item, str(item))
        for item in module_entries
    )

    return ProjectPaths(
        root=root,
        content_dir=content_dir,
        posts_dir=content_dir / "posts",
        content_images_dir=content_dir / "images",
        templates_dir=templates_dir,
        static_dir=static_dir,
        output_dir=output_dir,
        deploy_config=deploy_config,
        site_configs=(content_dir / "site.yaml", content_dir / "site.yml"),
        image_configs=(content_dir / "images.yaml", content_dir / "images.yml"),
        post_sidebar_configs=(content_dir / "post-sidebar.yaml", content_dir / "post-sidebar.yml"),
        watched_dirs=(content_dir, templates_dir, static_dir),
        watched_files=(config_file, *python_modules),
        python_modules=python_modules,
        vendor=normalize_vendor_config(raw.get("vendor")),
    )


def default_config_project() -> ProjectPaths:
    config_file = Path.cwd() / DEFAULT_CONFIG_FILE
    return project_from_config(config_file) if config_file.exists() else conventional_project(Path.cwd())
