"""Build orchestration for a Colophon site.

Data flows from ``ProjectPaths`` through config/content loading, context
enrichment, asset copying, image resolution, and final template rendering.
"""

from __future__ import annotations

import shutil

from .collections import attach_page_graph, enrich_post_context, is_post_context, should_list_page, summarize_page
from .content import build_page_context, build_source_chain, discover_routes, load_post_sidebar, load_site_config, scan_content_tree
from .expressions import expression_registry, resolve_page_context_expressions
from .images import copy_content_images, copy_referenced_assets, load_images, make_image_resolver
from .models import PageContext, ProjectPaths, RenderJob, SiteConfig, SourceFiles
from .project import project_or_default
from .render import make_environment, render_auxiliary_pages, render_template, route_to_output_path, select_template
from .vendor import required_vendor_assets, validate_local_vendor_assets


def reset_output(project: ProjectPaths | None = None) -> None:
    resolved_project = project_or_default(project)

    if resolved_project.output_dir.exists():
        shutil.rmtree(resolved_project.output_dir)

    resolved_project.output_dir.mkdir(parents=True)


def copy_static_assets(project: ProjectPaths | None = None) -> None:
    resolved_project = project_or_default(project)

    if not resolved_project.static_dir.exists():
        return

    for item in resolved_project.static_dir.iterdir():
        destination = resolved_project.output_dir / item.name

        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def build_contexts(
    site_config: SiteConfig,
    content_index: SourceFiles,
    post_sidebar: Mapping[str, Any],
    project: ProjectPaths | None = None,
) -> list[PageContext]:
    registry = expression_registry(project)
    initial_contexts = [
        resolve_page_context_expressions(
            build_page_context(route, build_source_chain(route, content_index), site_config, project),
            registry=registry,
        )
        for route in discover_routes(content_index)
    ]
    page_summaries = [
        summarize_page(context)
        for context in initial_contexts
        if should_list_page(context)
    ]
    graph_contexts = [
        attach_page_graph(context, page_summaries)
        for context in initial_contexts
    ]
    post_summaries = [
        summarize_page(context)
        for context in graph_contexts
        if is_post_context(context) and should_list_page(context)
    ]

    return [
        enrich_post_context(context, post_sidebar, post_summaries, registry)
        for context in graph_contexts
    ]


def build_render_jobs(
    contexts: list[PageContext],
    site_config: SiteConfig,
    project: ProjectPaths | None = None,
) -> list[RenderJob]:
    return [
        RenderJob(
            route=context.route,
            template_file=select_template(context.route, context, site_config),
            page_context=context,
            output_path=route_to_output_path(context.route, project),
        )
        for context in contexts
    ]


def load_project_contexts(project: ProjectPaths | None = None) -> tuple[SiteConfig, list[PageContext]]:
    resolved_project = project_or_default(project)
    site_config = load_site_config(resolved_project)
    post_sidebar = load_post_sidebar(resolved_project)
    content_index = scan_content_tree(resolved_project.content_dir)
    contexts = build_contexts(site_config, content_index, post_sidebar, resolved_project)
    return site_config, contexts


def resolve_required_vendor_assets(project: ProjectPaths | None = None) -> tuple[str, ...]:
    resolved_project = project_or_default(project)
    site_config, contexts = load_project_contexts(resolved_project)
    return required_vendor_assets(resolved_project, site_config, contexts)


def build_site(project: ProjectPaths | None = None) -> None:
    resolved_project = project_or_default(project)
    site_config, contexts = load_project_contexts(resolved_project)
    images = load_images(resolved_project)
    render_jobs = build_render_jobs(contexts, site_config, resolved_project)
    vendor_assets = required_vendor_assets(resolved_project, site_config, contexts)
    post_summaries = [
        summarize_page(context)
        for context in contexts
        if is_post_context(context) and should_list_page(context)
    ]

    validate_local_vendor_assets(resolved_project, vendor_assets)
    reset_output(resolved_project)
    copy_static_assets(resolved_project)
    copy_content_images(resolved_project)
    copy_referenced_assets(render_jobs, resolved_project)

    env = make_environment(
        site_config.data["site"],
        make_image_resolver(images, resolved_project),
        resolved_project,
        vendor_assets=vendor_assets,
    )

    for job in render_jobs:
        render_template(env, job)

    render_auxiliary_pages(env, site_config.data["site"], post_summaries, resolved_project)
