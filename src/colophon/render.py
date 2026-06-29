"""Jinja environment setup and page rendering.

Resolved page contexts and image resolvers flow into selected templates, output
paths, archive/tag/feed pages, and final HTML files.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from jinja2 import Environment, FileSystemLoader, pass_context, select_autoescape
from slugify import slugify

from .collections import sorted_pages
from .models import PageContext, ProjectPaths, RenderJob, Route, SiteConfig
from .project import project_or_default
from .utils import bool_value, deep_merge, mapping_value, public_url
from .vendor import vendor_url_for


@pass_context
def fmt_filter(ctx: Any, value: Any) -> str:
    site = ctx.get("site") or {}

    try:
        return str(value).format(**site)
    except Exception:
        return str(value)


def date_filter(value: Any, fmt: str = "%B %-d, %Y") -> str:
    if hasattr(value, "strftime"):
        return value.strftime(fmt).replace(" 0", " ")

    return str(value or "")


def make_environment(
    site: Mapping[str, Any],
    image_resolver: Any,
    project: ProjectPaths | None = None,
    *,
    vendor_assets: Iterable[str] = (),
) -> Environment:
    resolved_project = project_or_default(project)
    active_vendor_assets = tuple(vendor_assets)
    env = Environment(
        loader=FileSystemLoader(resolved_project.templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["date"] = date_filter
    env.filters["slugify"] = slugify
    env.filters["fmt"] = fmt_filter
    env.globals["public_url"] = lambda path: public_url(site, path)
    env.globals["image"] = image_resolver
    env.globals["vendor_url"] = lambda name, path="": vendor_url_for(
        resolved_project,
        active_vendor_assets,
        str(name),
        str(path or ""),
    )
    env.globals["vendor_enabled"] = lambda name: str(name) in active_vendor_assets
    env.globals["site"] = site
    return env


def page_uses_mastodon_timeline(context: Mapping[str, Any]) -> bool:
    mastodon = mapping_value(context.get("site", {}).get("mastodon"))
    timeline = mapping_value(mastodon.get("timeline"))
    sidebar = mapping_value(context.get("sidebar"))
    cards = sidebar.get("cards") if isinstance(sidebar.get("cards"), list) else []

    return bool_value(timeline.get("enabled")) and any(
        isinstance(card, Mapping) and card.get("type") == "mastodon_timeline"
        for card in cards
    )


def context_for_template(page_context: PageContext) -> dict[str, Any]:
    context = deep_merge(page_context.data, page_context.slots)
    context["assets"] = sorted(page_context.assets)
    context["uses_mastodon_timeline"] = page_uses_mastodon_timeline(context)
    context["page"] = {
        "route": page_context.route.url_path,
        "source_chain": [source.content_path for source in page_context.source_chain],
    }
    context["post"] = context
    return context


def matches_route(route: Route, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return route.url_path.startswith(prefix)

    return route.url_path == pattern


def specificity_of_match(route: Route, pattern: str) -> int:
    if not matches_route(route, pattern):
        return -1

    return len(pattern.removesuffix("**"))


def select_template(route: Route, page_context: PageContext, site_config: SiteConfig) -> str:
    template_name = page_context.data.get("template") or page_context.template

    if not template_name:
        matching_routes = [
            rule
            for rule in site_config.routes
            if matches_route(route, str(rule.get("match") or ""))
        ]
        best = max(
            matching_routes,
            key=lambda rule: specificity_of_match(route, str(rule.get("match") or "")),
            default={"template": "default"},
        )
        template_name = best.get("template") or "default"

    return site_config.templates.get(str(template_name), str(template_name))


def route_to_output_path(route: Route, project: ProjectPaths | None = None) -> Path:
    resolved_project = project_or_default(project)
    return (
        resolved_project.output_dir / "index.html"
        if route.url_path == "/"
        else resolved_project.output_dir / route.url_path.strip("/") / "index.html"
    )


def render_template(env: Environment, render_job: RenderJob) -> None:
    html = env.get_template(render_job.template_file).render(context_for_template(render_job.page_context))
    render_job.output_path.parent.mkdir(parents=True, exist_ok=True)
    render_job.output_path.write_text(html, encoding="utf-8")


def tag_groups(post_summaries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    tags: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for post in post_summaries:
        for tag in post.get("tags") or []:
            tags[str(tag)].append(post)

    return dict(tags)


def render_auxiliary_pages(
    env: Environment,
    site: Mapping[str, Any],
    post_summaries: list[dict[str, Any]],
    project: ProjectPaths | None = None,
) -> None:
    resolved_project = project_or_default(project)
    posts_by_date = sorted_pages(post_summaries, "date desc")
    tags = tag_groups(posts_by_date)

    (resolved_project.output_dir / "archive").mkdir(parents=True, exist_ok=True)
    (resolved_project.output_dir / "archive" / "index.html").write_text(
        env.get_template("archive.html").render(site=site, posts=posts_by_date, tags=tags),
        encoding="utf-8",
    )

    for tag, posts in sorted(tags.items()):
        tag_dir = resolved_project.output_dir / "tags" / slugify(tag)
        tag_dir.mkdir(parents=True, exist_ok=True)
        (tag_dir / "index.html").write_text(
            env.get_template("tag.html").render(site=site, tag=tag, posts=posts, tags=tags),
            encoding="utf-8",
        )

    (resolved_project.output_dir / "feed.xml").write_text(
        env.get_template("feed.xml").render(
            site=site,
            posts=posts_by_date[:20],
            build_date=dt.datetime.now(dt.UTC),
        ),
        encoding="utf-8",
    )
