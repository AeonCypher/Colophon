"""Shared dataclasses and callable type aliases.

Subsystems pass immutable ``ProjectPaths``, content contexts, render jobs, and
deploy state through the pipeline instead of mutating global state.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ExpressionFunction = Callable[[], Any]


MastodonPoster = Callable[[Mapping[str, Any], str, bool], dict[str, Any]]


TransportUploader = Callable[[Mapping[str, Any], Path, bool], list[str]]


@dataclass(frozen=True)
class VendorAssetOverride:
    enabled: bool | None = None
    local_path: str | None = None
    cdn_base: str | None = None
    required_files: tuple[str, ...] = ()
    cdn_files: tuple[tuple[str, str], ...] = ()
    dependencies: tuple[str, ...] = ()
    archive_url: str | None = None
    archive_prefix: str | None = None


@dataclass(frozen=True)
class VendorConfig:
    mode: str = "auto"
    local_dir: str = "vendor"
    required: tuple[str, ...] = ()
    assets: tuple[tuple[str, VendorAssetOverride], ...] = ()


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    content_dir: Path
    posts_dir: Path
    content_images_dir: Path
    templates_dir: Path
    static_dir: Path
    output_dir: Path
    deploy_config: Path
    site_configs: tuple[Path, ...]
    image_configs: tuple[Path, ...]
    post_sidebar_configs: tuple[Path, ...]
    watched_dirs: tuple[Path, ...]
    watched_files: tuple[Path, ...]
    python_modules: tuple[Path, ...] = ()
    vendor: VendorConfig = field(default_factory=VendorConfig)


@dataclass(frozen=True)
class SiteConfig:
    data: dict[str, Any]
    templates: dict[str, str]
    routes: list[dict[str, Any]]


@dataclass(frozen=True)
class Route:
    url_path: str


@dataclass(frozen=True)
class SourceFile:
    absolute_path: Path
    content_path: str
    kind: str


@dataclass(frozen=True)
class SourceFiles:
    source_files: tuple[SourceFile, ...]
    path_map: dict[str, SourceFile]

    @classmethod
    def from_files(cls, source_files: list[SourceFile]) -> "SourceFiles":
        return cls(
            source_files=tuple(source_files),
            path_map={source.content_path: source for source in source_files},
        )

    def by_content_path(self, content_path: str) -> SourceFile | None:
        return self.path_map.get(content_path)

    def by_kind(self, kind: str) -> list[SourceFile]:
        return [source for source in self.source_files if source.kind == kind]


@dataclass(frozen=True)
class ContentLayer:
    source_file: SourceFile
    route: Route
    data: dict[str, Any] = field(default_factory=dict)
    slots: dict[str, str] = field(default_factory=dict)
    assets: frozenset[str] = field(default_factory=frozenset)
    template: str | None = None


@dataclass(frozen=True)
class PageContext:
    route: Route
    data: dict[str, Any]
    slots: dict[str, str]
    assets: frozenset[str]
    template: str | None
    source_chain: tuple[SourceFile, ...]


@dataclass(frozen=True)
class RenderJob:
    route: Route
    template_file: str
    page_context: PageContext
    output_path: Path


@dataclass(frozen=True)
class DeployPostSelection:
    context: PageContext
    summary: dict[str, Any]
    source_file: SourceFile


@dataclass(frozen=True)
class DeployState:
    project: ProjectPaths
    config: dict[str, Any]
    target_name: str
    target_config: dict[str, Any]
    post_id: str | None
    dry_run: bool
    force_post: bool
    mastodon_poster: MastodonPoster
    transport_uploaders: Mapping[str, TransportUploader]
    site_config: SiteConfig | None = None
    contexts: tuple[PageContext, ...] = ()
    selection: DeployPostSelection | None = None
    status_text: str = ""
    status_url: str = ""
    posted: bool = False
    uploaded: bool = False
    upload_actions: tuple[str, ...] = ()
