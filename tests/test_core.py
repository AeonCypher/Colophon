from __future__ import annotations

import datetime as dt
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_TEMPLATES = REPO_ROOT / "tests" / "fixtures" / "templates"

sys.path.insert(0, str(REPO_ROOT / "src"))

from tests import colophon_test_api as colophon


@contextmanager
def isolated_paths():
    old = {
        "ROOT": colophon.ROOT,
        "CONTENT": colophon.CONTENT,
        "POSTS": colophon.POSTS,
        "CONTENT_IMAGES": colophon.CONTENT_IMAGES,
        "TEMPLATES": colophon.TEMPLATES,
        "STATIC": colophon.STATIC,
        "OUT": colophon.OUT,
        "DEPLOY_CONFIG": colophon.DEPLOY_CONFIG,
        "SITE_CONFIGS": colophon.SITE_CONFIGS,
        "IMAGE_CONFIGS": colophon.IMAGE_CONFIGS,
        "POST_SIDEBAR_CONFIGS": colophon.POST_SIDEBAR_CONFIGS,
        "WATCHED_DIRS": colophon.WATCHED_DIRS,
        "WATCHED_FILES": colophon.WATCHED_FILES,
    }

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        colophon.ROOT = root
        colophon.CONTENT = root / "content"
        colophon.POSTS = colophon.CONTENT / "posts"
        colophon.CONTENT_IMAGES = colophon.CONTENT / "images"
        colophon.TEMPLATES = root / "templates"
        colophon.STATIC = root / "static"
        colophon.OUT = root / "_site"
        colophon.DEPLOY_CONFIG = colophon.CONTENT / "deploy.yaml"
        colophon.SITE_CONFIGS = [colophon.CONTENT / "site.yaml", colophon.CONTENT / "site.yml"]
        colophon.IMAGE_CONFIGS = [colophon.CONTENT / "images.yaml", colophon.CONTENT / "images.yml"]
        colophon.POST_SIDEBAR_CONFIGS = [
            colophon.CONTENT / "post-sidebar.yaml",
            colophon.CONTENT / "post-sidebar.yml",
        ]
        colophon.WATCHED_DIRS = [colophon.CONTENT, colophon.TEMPLATES, colophon.STATIC]
        colophon.WATCHED_FILES = [root / "colophon.py"]

        for path in [colophon.CONTENT, colophon.POSTS, colophon.CONTENT_IMAGES, colophon.TEMPLATES, colophon.STATIC, colophon.OUT]:
            path.mkdir(parents=True, exist_ok=True)

        try:
            yield root
        finally:
            for name, value in old.items():
                setattr(colophon, name, value)


def right_detail_image():
    from PIL import ImageDraw

    image = colophon.Image.new("RGB", (120, 60), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)

    for x in range(82, 114, 4):
        draw.line((x, 8, x, 52), fill=(255, 255, 255), width=1)

    for y in range(8, 52, 4):
        draw.line((82, y, 114, y), fill=(255, 255, 255), width=1)

    return image


def source_file(slug: str) -> colophon.SourceFile:
    return colophon.SourceFile(Path(f"/tmp/{slug}.md"), f"posts/{slug}.md", "markdown")


def post_context(
    slug: str,
    date: dt.date,
    *,
    status: str = "published",
    draft: bool = False,
    listed: bool = True,
) -> colophon.PageContext:
    data = {
        "slug": slug,
        "title": slug.title(),
        "date": date,
        "status": status,
        "summary": f"{slug} summary",
        "tags": [],
        "draft": draft,
        "listed": listed,
    }

    return colophon.PageContext(
        route=colophon.Route(f"/posts/{slug}/"),
        data=data,
        slots={},
        assets=frozenset(),
        template="post",
        source_chain=(source_file(slug),),
    )


def write_minimal_deploy_site() -> None:
    colophon.TEMPLATES = FIXTURE_TEMPLATES
    (colophon.CONTENT / "site.yaml").write_text(
        """
site:
  title: Test
  url: https://example.test
  mastodon:
    enabled: true
    host: social.example
    instance_url: https://social.example
    user: alice
""",
        encoding="utf-8",
    )
    (colophon.CONTENT / "index.yml").write_text(
        """
template: page
title: Home
posts_section:
  featured: {}
""",
        encoding="utf-8",
    )
    (colophon.CONTENT / "post-sidebar.yml").write_text("cards: []\n", encoding="utf-8")
    (colophon.POSTS / "older.md").write_text(
        """---
title: Older
slug: older
date: 2026-01-01
summary: Older summary
status: published
---

## Body
""",
        encoding="utf-8",
    )
    (colophon.POSTS / "newer.md").write_text(
        """---
title: Newer
slug: newer
date: 2026-02-01
summary: Newer summary
status: published
---

## Body
""",
        encoding="utf-8",
    )
    (colophon.CONTENT / "deploy.yaml").write_text(
        """
deploy:
  default_target: production
  mastodon:
    access_token: env::MASTODON_ACCESS_TOKEN
    post_text: "{{ post.title }} {{ post.url }}"
  targets:
    production:
      transport: ftps
      host: example.test
      username: deploy
      password: env::LIBERTAI_FTP_PASSWORD
      remote_path: public_html/example.test/
""",
        encoding="utf-8",
    )


class ColophonTests(unittest.TestCase):
    def test_deep_merge_replaces_lists(self) -> None:
        base = {"sidebar": {"cards": [{"title": "old"}]}, "meta": {"a": 1, "b": 2}}
        override = {"sidebar": {"cards": [{"title": "new"}]}, "meta": {"b": 3}}

        self.assertEqual(
            colophon.deep_merge(base, override),
            {"sidebar": {"cards": [{"title": "new"}]}, "meta": {"a": 1, "b": 3}},
        )
        self.assertEqual(base["sidebar"]["cards"][0]["title"], "old")

    def test_yaml_function_resolution_uses_injected_registry_once_per_node(self) -> None:
        calls: list[str] = []

        def value() -> str:
            calls.append("value")
            return f"value-{len(calls)}"

        result = colophon.resolve_yaml_expressions(
            {"token": "python::value", "copy": "{{ token }}"},
            registry={"value": value},
        )

        self.assertEqual(result, {"token": "value-1", "copy": "value-1"})
        self.assertEqual(calls, ["value"])

    def test_yaml_expression_resolution_is_recursive_and_immutable(self) -> None:
        source = {
            "label": "Rune",
            "items": [
                "python::color",
                {"text": "Marked {{ label }}"},
            ],
        }
        original = colophon.copy_value(source)

        result = colophon.resolve_yaml_expressions(
            source,
            registry={"color": lambda: "CYAN"},
        )

        self.assertEqual(
            result,
            {
                "label": "Rune",
                "items": [
                    "CYAN",
                    {"text": "Marked Rune"},
                ],
            },
        )
        self.assertEqual(source, original)

    def test_yaml_function_results_are_copied_for_nested_structures(self) -> None:
        generated = {"icons": [{"src": "/assets/test.png", "alt": "test icon"}]}

        result = colophon.resolve_yaml_expressions(
            {"altar": "python::icons"},
            registry={"icons": lambda: generated},
        )

        result["altar"]["icons"][0]["src"] = "/assets/changed.png"

        self.assertEqual(generated["icons"][0]["src"], "/assets/test.png")

    def test_resolve_site_expressions_formats_signal_line_mapping_in_order(self) -> None:
        result = colophon.resolve_site_expressions(
            {
                "author": "Alice",
                "signal_line": {
                    "SIGNAL": "python::color",
                    "MOON": "{{ site.author }}",
                    "FEED": "HAND-CURATED",
                },
            },
            registry={"color": lambda: "CYAN"},
        )

        self.assertEqual(
            result["signal_line"],
            "SIGNAL: CYAN // MOON: Alice // FEED: HAND-CURATED",
        )

    def test_unknown_yaml_function_fails_with_path(self) -> None:
        with self.assertRaisesRegex(
            colophon.ExpressionResolutionError,
            r"site\.signal_line\.SIGNAL.*missing",
        ):
            colophon.resolve_yaml_expressions(
                {"site": {"signal_line": {"SIGNAL": "python::missing"}}},
                registry={},
                path="",
            )

    def test_missing_yaml_template_variable_fails_with_path(self) -> None:
        with self.assertRaisesRegex(
            colophon.ExpressionResolutionError,
            r"sidebar\.text.*missing",
        ):
            colophon.resolve_yaml_expressions(
                {"sidebar": {"text": "Operator {{ missing }}"}},
                path="",
            )

    def test_env_resolution_reads_environment_and_preserves_source(self) -> None:
        source = {"deploy": {"password": "env::TEST_DEPLOY_PASSWORD"}}

        with patch.dict(os.environ, {"TEST_DEPLOY_PASSWORD": "secret"}, clear=False):
            result = colophon.resolve_yaml_expressions(source)

        self.assertEqual(result["deploy"]["password"], "secret")
        self.assertEqual(source["deploy"]["password"], "env::TEST_DEPLOY_PASSWORD")

    def test_missing_env_resolution_fails_with_path(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                colophon.ExpressionResolutionError,
                r"deploy\.targets\.production\.password.*MISSING_PASSWORD",
            ):
                colophon.resolve_env_references(
                    {
                        "targets": {
                            "production": {
                                "password": "env::MISSING_PASSWORD",
                            }
                        }
                    },
                    "deploy",
                )

    def test_deploy_config_normalizes_defaults_and_redacts_secrets(self) -> None:
        raw = {
            "deploy": {
                "mastodon": {"access_token": "env::MASTODON_ACCESS_TOKEN"},
                "targets": {
                    "production": {
                        "transport": "ftps",
                        "host": "example.test",
                        "username": "deploy",
                        "password": "env::LIBERTAI_FTP_PASSWORD",
                        "remote_path": "public_html/example.test/",
                    }
                },
            }
        }

        with patch.dict(
            os.environ,
            {
                "MASTODON_ACCESS_TOKEN": "mastodon-token",
                "LIBERTAI_FTP_PASSWORD": "ftp-password",
            },
            clear=False,
        ):
            config = colophon.normalize_deploy_config(raw)

        target = config["targets"]["production"]
        redacted = colophon.redact_secrets({"mastodon": config["mastodon"], "target": target})

        self.assertEqual(config["steps"], colophon.DEFAULT_DEPLOY_STEPS)
        self.assertEqual(target["port"], 21)
        self.assertEqual(target["password"], "ftp-password")
        self.assertEqual(redacted["mastodon"]["access_token"], "[redacted]")
        self.assertEqual(redacted["target"]["password"], "[redacted]")

    def test_select_deploy_post_uses_latest_published_and_post_id_override(self) -> None:
        contexts = [
            post_context("older", dt.date(2026, 1, 1)),
            post_context("newer", dt.date(2026, 2, 1)),
            post_context("draft", dt.date(2026, 3, 1), status="draft-ready"),
            post_context("hidden", dt.date(2026, 4, 1), listed=False),
        ]

        latest = colophon.select_deploy_post(contexts)
        older = colophon.select_deploy_post(contexts, post_id="older")

        self.assertEqual(latest.summary["slug"], "newer")
        self.assertEqual(older.summary["slug"], "older")

    def test_mastodon_post_text_renders_post_site_context(self) -> None:
        selection = colophon.select_deploy_post([post_context("newer", dt.date(2026, 2, 1))])
        text = colophon.render_mastodon_post_text(
            {"post_text": "{{ site.title }}: {{ post.title }} {{ post.summary }} {{ post.url }}"},
            selection,
            {"title": "Site", "url": "https://example.test"},
        )

        self.assertEqual(
            text,
            "Site: Newer newer summary https://example.test/posts/newer/",
        )

    def test_mastodon_site_config_defaults_merge_immutably(self) -> None:
        raw = {
            "enabled": True,
            "host": "social.example",
            "user": "alice",
            "user_id": "42",
            "profile_name": "@alice",
            "timeline": {"maxNbPostShow": "3"},
        }

        result = colophon.normalize_mastodon_site_config(raw)

        self.assertTrue(result["enabled"])
        self.assertEqual(result["host"], "social.example")
        self.assertEqual(result["instance_url"], "https://social.example")
        self.assertTrue(result["timeline"]["enabled"])
        self.assertEqual(result["timeline"]["container_id"], "mastodon-timeline")
        self.assertEqual(result["timeline"]["options"]["timelineType"], "profile")
        self.assertEqual(result["timeline"]["options"]["userId"], "42")
        self.assertEqual(result["timeline"]["options"]["profileName"], "@alice")
        self.assertEqual(result["timeline"]["options"]["maxNbPostShow"], "3")
        self.assertEqual(colophon.DEFAULT_MASTODON_TIMELINE["instanceUrl"], "")
        self.assertNotIn("instanceUrl", raw["timeline"])

    def test_mastodon_site_config_ignores_placeholder_instance_url_when_host_is_real(self) -> None:
        result = colophon.normalize_mastodon_site_config(
            {
                "enabled": True,
                "host": "https://lgbtqia.space",
                "instance_url": "https://mastodon.example",
                "user_id": "111835162007920375",
                "profile_name": "@AeonCypher",
                "timeline": {"enabled": True},
            }
        )

        self.assertEqual(result["host"], "lgbtqia.space")
        self.assertEqual(result["instance_url"], "https://lgbtqia.space")
        self.assertEqual(result["timeline"]["options"]["instanceUrl"], "https://lgbtqia.space")
        self.assertEqual(result["timeline"]["options"]["userId"], "111835162007920375")

    def test_load_site_config_normalizes_mastodon_before_default_merge(self) -> None:
        with isolated_paths():
            (colophon.CONTENT / "site.yaml").write_text(
                """
site:
  mastodon:
    enabled: true
    host: https://lgbtqia.space
    instance_url: https://mastodon.example
    user: AeonCypher
    user_id: "111835162007920375"
    profile_name: "@AeonCypher"
    timeline:
      enabled: true
""",
                encoding="utf-8",
            )

            timeline = colophon.load_site_config().data["site"]["mastodon"]["timeline"]

        self.assertTrue(timeline["enabled"])
        self.assertEqual(timeline["options"]["instanceUrl"], "https://lgbtqia.space")
        self.assertEqual(timeline["options"]["userId"], "111835162007920375")
        self.assertEqual(timeline["options"]["profileName"], "@AeonCypher")

    def test_mastodon_comments_explicit_config_uses_site_defaults(self) -> None:
        site = colophon.normalize_mastodon_site_config(
            {"host": "social.example", "user": "alice"}
        )

        result = colophon.normalize_mastodon_comments(
            {"enabled": True, "toot_id": "123"},
            site,
        )

        self.assertEqual(
            {key: result[key] for key in ("enabled", "host", "user", "toot_id")},
            {
                "enabled": True,
                "host": "social.example",
                "user": "alice",
                "toot_id": "123",
            },
        )

    def test_mastodon_comments_status_url_extracts_thread_fields(self) -> None:
        site = colophon.normalize_mastodon_site_config({})

        result = colophon.normalize_mastodon_comments(
            {"status_url": "https://mastodon.social/@alice/109876", "lang": "fr"},
            site,
        )

        self.assertTrue(result["enabled"])
        self.assertEqual(result["host"], "mastodon.social")
        self.assertEqual(result["user"], "alice")
        self.assertEqual(result["toot_id"], "109876")
        self.assertEqual(result["lang"], "fr")

    def test_mastodon_comments_missing_or_disabled_do_not_enable_component(self) -> None:
        site = colophon.normalize_mastodon_site_config(
            {"host": "social.example", "user": "alice"}
        )

        missing = colophon.normalize_mastodon_comments(None, site)
        disabled = colophon.normalize_mastodon_comments(
            {
                "enabled": False,
                "status_url": "https://social.example/@alice/123",
            },
            site,
        )

        self.assertFalse(missing["enabled"])
        self.assertFalse(disabled["enabled"])

    def test_mastodon_site_config_does_not_include_comment_config(self) -> None:
        result = colophon.normalize_mastodon_site_config(
            {
                "host": "social.example",
                "user": "alice",
                "comments": {
                    "enabled": True,
                    "threads": {
                        "threaded": "https://social.example/@alice/456",
                    },
                },
            }
        )

        self.assertNotIn("comments", result)

    def test_route_discovery_excludes_support_files_and_image_docs(self) -> None:
        with isolated_paths():
            (colophon.CONTENT / "site.yaml").write_text("site:\n  title: Test\n", encoding="utf-8")
            (colophon.CONTENT / "images.yml").write_text("images: {}\n", encoding="utf-8")
            (colophon.CONTENT / "post-sidebar.yml").write_text("cards: []\n", encoding="utf-8")
            (colophon.CONTENT / "deploy.yaml").write_text("deploy:\n  targets: {}\n", encoding="utf-8")
            (colophon.CONTENT / "index.yml").write_text("template: page\n", encoding="utf-8")
            (colophon.CONTENT_IMAGES / "README.md").write_text("# images\n", encoding="utf-8")
            (colophon.POSTS / "one.md").write_text("---\ntitle: One\n---\n\nBody\n", encoding="utf-8")

            routes = [route.url_path for route in colophon.discover_routes(colophon.scan_content_tree(colophon.CONTENT))]

        self.assertEqual(routes, ["/", "/posts/one/"])

    def test_static_pages_route_without_pages_prefix(self) -> None:
        with isolated_paths():
            pages = colophon.CONTENT / "pages"
            nested = pages / "rituals"
            nested.mkdir(parents=True)
            (pages / "about.md").write_text("---\ntitle: About\n---\n\nBody\n", encoding="utf-8")
            (pages / "legal.yml").write_text("title: Legal\n", encoding="utf-8")
            (nested / "index.md").write_text("---\ntitle: Rituals\n---\n\nBody\n", encoding="utf-8")

            routes = [
                route.url_path
                for route in colophon.discover_routes(colophon.scan_content_tree(colophon.CONTENT))
            ]

        self.assertEqual(routes, ["/about/", "/legal/", "/rituals/"])

    def test_static_pages_render_with_default_simple_template(self) -> None:
        with isolated_paths():
            colophon.TEMPLATES = FIXTURE_TEMPLATES
            pages = colophon.CONTENT / "pages"
            pages.mkdir()
            (colophon.CONTENT / "site.yaml").write_text("site:\n  title: Test\n", encoding="utf-8")
            (pages / "about.md").write_text(
                """
---
summary: A static about page.
---

## About

Static **body**.
""",
                encoding="utf-8",
            )

            colophon.build_site()

            about = (colophon.OUT / "about" / "index.html").read_text(encoding="utf-8")

        self.assertIn("<title>About</title>", about)
        self.assertIn('<h2 id="about">About</h2>', about)
        self.assertIn("<strong>body</strong>", about)
        self.assertNotIn("Latest transmissions", about)

    def test_default_posts_collection_sorts_date_desc(self) -> None:
        pages = [
            {"route": "/posts/older/", "date": dt.date(2024, 1, 1), "tags": []},
            {"route": "/about/", "date": dt.date(2026, 1, 1), "tags": []},
            {"route": "/posts/newer/", "date": dt.date(2024, 2, 1), "tags": []},
        ]

        collections = colophon.build_collections({}, pages)

        self.assertEqual(
            [page["route"] for page in collections["posts"]],
            ["/posts/newer/", "/posts/older/"],
        )

    def test_sorted_pages_orders_date_desc(self) -> None:
        pages = [
            {"route": "/posts/older/", "date": dt.date(2024, 1, 1)},
            {"route": "/posts/newer/", "date": dt.date(2024, 2, 1)},
        ]

        self.assertEqual(
            [page["route"] for page in colophon.sorted_pages(pages, "date desc")],
            ["/posts/newer/", "/posts/older/"],
        )

    def test_markdown_preserves_inline_html_and_builds_toc(self) -> None:
        html, toc = colophon.render_markdown(
            "## Diagram\n\n<figure class=\"placeholder\"><figcaption>ok</figcaption></figure>\n"
        )

        self.assertIn('<h2 id="diagram">Diagram</h2>', html)
        self.assertIn('<figure class="placeholder">', html)
        self.assertNotIn("&lt;figure", html)
        self.assertEqual(toc, [{"id": "diagram", "text": "Diagram"}])

    @unittest.skipIf(colophon.Image is None, "Pillow is not installed")
    def test_auto_crop_position_tracks_off_center_detail(self) -> None:
        x, y = colophon.smart_crop_position(right_detail_image(), (60, 60))

        self.assertGreater(x, 0.6)
        self.assertAlmostEqual(y, 0.5, delta=0.2)

    @unittest.skipIf(colophon.Image is None, "Pillow is not installed")
    def test_auto_crop_position_falls_back_for_flat_images(self) -> None:
        image = colophon.Image.new("RGB", (120, 60), color=(32, 32, 32))

        self.assertEqual(colophon.smart_crop_position(image, (60, 60)), (0.5, 0.5))

    @unittest.skipIf(colophon.Image is None, "Pillow is not installed")
    def test_image_resolver_returns_auto_crop_position(self) -> None:
        with isolated_paths():
            source = colophon.CONTENT_IMAGES / "wide.png"
            right_detail_image().save(source)
            resolver = colophon.make_image_resolver(
                {
                    "wide": {
                        "file": "wide.png",
                        "width": 60,
                        "height": 60,
                        "crop": "auto",
                    }
                }
            )

            result = resolver("wide")

            self.assertTrue(result["exists"])
            self.assertGreater(colophon.parse_position(result["position"])[0], 0.6)

    @unittest.skipIf(colophon.Image is None, "Pillow is not installed")
    def test_image_resolver_generates_derivative_and_missing_placeholder(self) -> None:
        with isolated_paths():
            source = colophon.CONTENT_IMAGES / "hero.png"
            colophon.Image.new("RGB", (32, 24), color=(255, 0, 255)).save(source)
            resolver = colophon.make_image_resolver(
                {
                    "hero": {
                        "file": "hero.png",
                        "alt": "Hero",
                        "width": 16,
                        "height": 12,
                    }
                }
            )

            image = resolver("hero")
            missing = resolver("missing")

            self.assertTrue(image["exists"])
            self.assertEqual(image["url"], "/images/generated/hero-base-16x12.png")
            self.assertTrue((colophon.OUT / "images" / "generated" / "hero-base-16x12.png").exists())
            self.assertFalse(missing["exists"])
            self.assertEqual(missing["label"], "missing")

    def test_load_images_resolves_registered_yaml_functions(self) -> None:
        with isolated_paths():
            (colophon.CONTENT / "images.yml").write_text(
                """
images:
  dynamic: python::image_config
""",
                encoding="utf-8",
            )

            with patch.dict(
                colophon.YAML_FUNCTIONS,
                {"image_config": lambda: {"file": "dynamic.png", "width": 12, "height": 6}},
                clear=False,
            ):
                images = colophon.load_images()

        self.assertEqual(
            images["dynamic"],
            {"file": "dynamic.png", "width": 12, "height": 6},
        )

    @unittest.skipIf(colophon.Image is None, "Pillow is not installed")
    def test_sidebar_image_resolves_through_active_post(self) -> None:
        with isolated_paths():
            source = colophon.CONTENT_IMAGES / "relic.png"
            colophon.Image.new("RGB", (20, 20), color=(0, 255, 255)).save(source)
            resolver = colophon.make_image_resolver(
                {
                    "post_sidebar_relic": {
                        "file": "relic.png",
                        "width": 10,
                        "height": 10,
                    }
                }
            )
            context = colophon.PageContext(
                route=colophon.Route("/posts/a/"),
                data={"slug": "a", "tags": ["tools"], "sidebar_image": "post_sidebar_relic"},
                slots={},
                assets=frozenset(),
                template=None,
                source_chain=(),
            )

            enriched = colophon.enrich_post_context(
                context,
                {"cards": [{"type": "image", "image": "sidebar_image"}]},
                [{"slug": "b", "url": "/posts/b/", "title": "B", "tags": ["tools"]}],
            )
            image = resolver("sidebar_image", post=enriched.data)

            self.assertEqual(enriched.data["sidebar"]["cards"][0]["image"], "sidebar_image")
            self.assertEqual(enriched.data["related"][0]["slug"], "b")
            self.assertTrue(image["exists"])
            self.assertEqual(image["key"], "post_sidebar_relic")

    def test_post_sidebar_expressions_resolve_after_post_enrichment(self) -> None:
        context = colophon.PageContext(
            route=colophon.Route("/posts/a/"),
            data={
                "title": "Post A",
                "slug": "a",
                "tags": [],
                "site": {"mastodon": {}},
            },
            slots={},
            assets=frozenset(),
            template=None,
            source_chain=(),
        )

        with patch.dict(
            colophon.YAML_FUNCTIONS,
            {"icons": lambda: [{"src": "/assets/test-icon.png", "alt": "test icon"}]},
            clear=False,
        ):
            enriched = colophon.enrich_post_context(
                context,
                {
                    "cards": [
                        {
                            "type": "altar",
                            "title": "{{ title }} altar",
                            "icons": "python::icons",
                        }
                    ]
                },
                [],
            )

        card = enriched.data["sidebar"]["cards"][0]

        self.assertEqual(card["title"], "Post A altar")
        self.assertEqual(card["icons"], [{"src": "/assets/test-icon.png", "alt": "test icon"}])

    def test_build_renders_mastodon_timeline_assets_and_enabled_comments_only(self) -> None:
        with isolated_paths():
            colophon.TEMPLATES = FIXTURE_TEMPLATES
            (colophon.CONTENT / "site.yaml").write_text(
                """
site:
  title: Test
  mastodon:
    enabled: true
    host: social.example
    instance_url: https://social.example
    user: alice
    user_id: "42"
    profile_name: "@alice"
    timeline:
      enabled: true
      mtContainerId: test-timeline
      maxNbPostShow: "3"
""",
                encoding="utf-8",
            )
            (colophon.CONTENT / "index.yml").write_text(
                """
template: page
title: Home
posts_section:
  featured: {}
sidebar:
  cards:
    - type: mastodon_timeline
      title: Fediverse
""",
                encoding="utf-8",
            )
            (colophon.CONTENT / "post-sidebar.yml").write_text("cards: []\n", encoding="utf-8")
            (colophon.POSTS / "with-comments.md").write_text(
                """
---
title: With comments
date: 2026-01-01
mastodon_comments:
  enabled: true
  status_url: https://social.example/@alice/123
  lang: en
---

## Body

Hello.
""",
                encoding="utf-8",
            )
            (colophon.POSTS / "without-comments.md").write_text(
                """
---
title: Without comments
date: 2026-01-02
---

## Body

Hello.
""",
                encoding="utf-8",
            )

            colophon.build_site()

            home = (colophon.OUT / "index.html").read_text(encoding="utf-8")
            with_comments = (colophon.OUT / "posts" / "with-comments" / "index.html").read_text(
                encoding="utf-8"
            )
            without_comments = (
                colophon.OUT / "posts" / "without-comments" / "index.html"
            ).read_text(encoding="utf-8")

        self.assertIn("/vendor/mastodon-embed-timeline/mastodon-timeline.min.css", home)
        self.assertIn("/vendor/mastodon-embed-timeline/mastodon-timeline.umd.js", home)
        self.assertIn("data-mastodon-timeline-config", home)
        self.assertIn('"mtContainerId": "test-timeline"', home)
        self.assertIn("<mastodon-comments", with_comments)
        self.assertIn('host="social.example"', with_comments)
        self.assertIn('user="alice"', with_comments)
        self.assertIn('tootId="123"', with_comments)
        self.assertIn("/vendor/dompurify/purify.min.js", with_comments)
        self.assertNotIn("<mastodon-comments", without_comments)
        self.assertNotIn("/vendor/dompurify/purify.min.js", without_comments)

    def test_build_resolves_signal_line_and_page_templates(self) -> None:
        with isolated_paths():
            colophon.TEMPLATES = FIXTURE_TEMPLATES
            (colophon.CONTENT / "site.yaml").write_text(
                """
site:
  title: Test
  author: Alice
  signal_line:
    SIGNAL: python::generate_random_color
    MOON: python::get_moon_phase
    FEED: HAND-CURATED
    SPELL CACHE: python::generate_random_temperature
""",
                encoding="utf-8",
            )
            (colophon.CONTENT / "index.yml").write_text(
                """
template: page
title: Home
posts_section:
  heading: Posts
  featured: {}
signal_color: python::generate_random_color
sidebar:
  cards:
    - type: profile
      title: Profile
      text: "Operator {{ site.author }} broadcasting {{ signal_color }} from {{ title }}"
""",
                encoding="utf-8",
            )

            colophon.build_site()

            home = (colophon.OUT / "index.html").read_text(encoding="utf-8")

        self.assertIn("SIGNAL:", home)
        self.assertIn("MOON:", home)
        self.assertIn("FEED: HAND-CURATED", home)
        self.assertIn("SPELL CACHE:", home)
        self.assertIn("Operator Alice broadcasting", home)
        self.assertIn("from Home", home)
        self.assertNotIn("python::", home)

    def test_build_resolves_nested_sidebar_icon_function_in_homepage_yaml(self) -> None:
        with isolated_paths():
            colophon.TEMPLATES = FIXTURE_TEMPLATES
            (colophon.CONTENT / "site.yaml").write_text(
                "site:\n  title: Test\n",
                encoding="utf-8",
            )
            (colophon.CONTENT / "index.yml").write_text(
                """
template: page
title: Home
posts_section:
  featured: {}
sidebar:
  cards:
    - type: altar
      title: Altar
      icons: python::test_icons
""",
                encoding="utf-8",
            )
            (colophon.CONTENT / "post-sidebar.yml").write_text("cards: []\n", encoding="utf-8")

            with patch.dict(
                colophon.YAML_FUNCTIONS,
                {"test_icons": lambda: [{"src": "/assets/test-icon.png", "alt": "test icon"}]},
                clear=False,
            ):
                colophon.build_site()

            home = (colophon.OUT / "index.html").read_text(encoding="utf-8")

        self.assertIn('<p class="asset-altar">', home)
        self.assertIn('<img src="/assets/test-icon.png" alt="test icon">', home)
        self.assertNotIn("python::", home)

    def test_build_links_and_copies_favicons(self) -> None:
        with isolated_paths():
            colophon.TEMPLATES = FIXTURE_TEMPLATES
            favicon_files = {
                "favicon.ico": b"ico",
                "favicon.png": b"png",
                "apple-touch-icon.png": b"apple",
            }

            for filename, content in favicon_files.items():
                (colophon.STATIC / filename).write_bytes(content)

            (colophon.CONTENT / "site.yaml").write_text(
                "site:\n  title: Test\n",
                encoding="utf-8",
            )
            (colophon.CONTENT / "index.yml").write_text(
                """
template: page
title: Home
posts_section:
  featured: {}
""",
                encoding="utf-8",
            )

            colophon.build_site()

            home = (colophon.OUT / "index.html").read_text(encoding="utf-8")
            copied_favicons = {
                filename: (colophon.OUT / filename).read_bytes()
                for filename in favicon_files
            }

        self.assertIn('rel="icon" href="/favicon.ico" sizes="any"', home)
        self.assertIn(
            'rel="icon" type="image/png" sizes="32x32" href="/favicon.png"',
            home,
        )
        self.assertIn('rel="apple-touch-icon" href="/apple-touch-icon.png"', home)
        self.assertIn("/vendor/webawesome/v3.8.0/styles/themes/awesome.css", home)
        self.assertNotIn("https://ka-f.webawesome.com", home)
        self.assertEqual(copied_favicons, favicon_files)

    def test_write_source_mastodon_status_url_handles_missing_enabled_and_disabled(self) -> None:
        cases = [
            (
                "---\ntitle: Missing\n---\n\nBody\n",
                {"enabled": True, "status_url": "https://social.example/@alice/1"},
            ),
            (
                "---\ntitle: Enabled\nmastodon_comments:\n  enabled: true\n  lang: en\n---\n\nBody\n",
                {
                    "enabled": True,
                    "lang": "en",
                    "status_url": "https://social.example/@alice/1",
                },
            ),
            (
                "---\ntitle: Disabled\nmastodon_comments:\n  enabled: false\n---\n\nBody\n",
                {"enabled": False, "status_url": "https://social.example/@alice/1"},
            ),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            for index, (body, expected) in enumerate(cases):
                path = Path(tmp) / f"post-{index}.md"
                path.write_text(body, encoding="utf-8")
                source = colophon.SourceFile(path, f"posts/post-{index}.md", "markdown")

                colophon.write_source_mastodon_status_url(
                    source,
                    "https://social.example/@alice/1",
                )

                metadata = colophon.frontmatter.loads(path.read_text(encoding="utf-8")).metadata
                self.assertEqual(metadata["mastodon_comments"], expected)

    def test_deploy_site_skips_repost_when_status_url_exists(self) -> None:
        with isolated_paths():
            write_minimal_deploy_site()
            newer = colophon.POSTS / "newer.md"
            newer.write_text(
                newer.read_text(encoding="utf-8").replace(
                    "status: published",
                    "status: published\nmastodon_comments:\n  enabled: true\n  status_url: https://social.example/@alice/old",
                ),
                encoding="utf-8",
            )
            posted: list[str] = []
            uploaded: list[tuple[str, bool]] = []

            def poster(mastodon: dict[str, str], status_text: str, dry_run: bool) -> dict[str, str]:
                posted.append(status_text)
                return {"url": "https://social.example/@alice/new"}

            def uploader(target: dict[str, object], source_dir: Path, dry_run: bool) -> list[str]:
                uploaded.append((str(target["remote_path"]), dry_run))
                return ["fake upload"]

            with patch.dict(
                os.environ,
                {
                    "MASTODON_ACCESS_TOKEN": "token",
                    "LIBERTAI_FTP_PASSWORD": "password",
                },
                clear=False,
            ):
                result = colophon.deploy_site(
                    mastodon_poster=poster,
                    transport_uploaders={"ftps": uploader},
                )

        self.assertEqual(posted, [])
        self.assertEqual(uploaded, [("public_html/example.test/", False)])
        self.assertEqual(result["status_url"], "https://social.example/@alice/old")
        self.assertFalse(result["posted"])
        self.assertTrue(result["uploaded"])

    def test_deploy_site_posts_enables_comments_rebuilds_and_uploads(self) -> None:
        with isolated_paths():
            write_minimal_deploy_site()
            posted: list[str] = []
            uploaded: list[bool] = []

            def poster(mastodon: dict[str, str], status_text: str, dry_run: bool) -> dict[str, str]:
                posted.append(status_text)
                return {"url": "https://social.example/@alice/new"}

            def uploader(target: dict[str, object], source_dir: Path, dry_run: bool) -> list[str]:
                uploaded.append((source_dir / "posts" / "newer" / "index.html").exists())
                return ["fake upload"]

            with patch.dict(
                os.environ,
                {
                    "MASTODON_ACCESS_TOKEN": "token",
                    "LIBERTAI_FTP_PASSWORD": "password",
                },
                clear=False,
            ):
                result = colophon.deploy_site(
                    mastodon_poster=poster,
                    transport_uploaders={"ftps": uploader},
                )

            metadata = colophon.frontmatter.loads(
                (colophon.POSTS / "newer.md").read_text(encoding="utf-8")
            ).metadata
            rendered = (colophon.OUT / "posts" / "newer" / "index.html").read_text(
                encoding="utf-8"
            )

        self.assertEqual(posted, ["Newer https://example.test/posts/newer/"])
        self.assertEqual(uploaded, [True])
        self.assertEqual(metadata["mastodon_comments"]["status_url"], "https://social.example/@alice/new")
        self.assertIn("<mastodon-comments", rendered)
        self.assertEqual(result["post_slug"], "newer")
        self.assertTrue(result["posted"])

    def test_upload_site_directory_uses_injected_transport_and_guards_purge_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "site"
            (source / "nested").mkdir(parents=True)
            (source / "nested" / "index.html").write_text("ok", encoding="utf-8")
            calls: list[tuple[str, bool]] = []

            def uploader(target: dict[str, object], source_dir: Path, dry_run: bool) -> list[str]:
                calls.append((str(target["transport"]), dry_run))
                return colophon.planned_upload_actions(target, source_dir)

            target = colophon.normalize_deploy_target(
                {
                    "transport": "ftps",
                    "host": "example.test",
                    "username": "deploy",
                    "password": "secret",
                    "remote_path": "public_html/example.test/",
                }
            )
            actions = colophon.upload_site_directory(
                target,
                source,
                True,
                {"ftps": uploader},
            )

        self.assertEqual(calls, [("ftps", True)])
        self.assertEqual(actions, ["purge then upload 1 file(s) to ftps://example.test/public_html/example.test/"])
        self.assertFalse(colophon.is_safe_remote_purge_path("public_html"))

    def test_cli_deploy_dry_run_smoke(self) -> None:
        with isolated_paths():
            write_minimal_deploy_site()

            with patch.dict(
                os.environ,
                {
                    "MASTODON_ACCESS_TOKEN": "token",
                    "LIBERTAI_FTP_PASSWORD": "password",
                },
                clear=False,
            ), patch.object(sys, "argv", ["build.py", "--deploy", "--dry-run"]):
                colophon.main()

            newer = colophon.frontmatter.loads(
                (colophon.POSTS / "newer.md").read_text(encoding="utf-8")
            ).metadata
            rendered = (colophon.OUT / "posts" / "newer" / "index.html").exists()

        self.assertNotIn("mastodon_comments", newer)
        self.assertTrue(rendered)


if __name__ == "__main__":
    unittest.main()
