"""Example trusted hook module copied into scaffolded sites.

The scaffold config loads ``YAML_FUNCTIONS`` so YAML expressions can inject
generated values into site and page data during a build.
"""

from __future__ import annotations


def demo_status() -> str:
    return "READY"


def demo_build_label() -> str:
    return "generated from site_hooks.py"


def demo_links() -> list[dict[str, str]]:
    return [
        {"label": "About routing", "href": "/about/"},
        {"label": "Feature tour", "href": "/features/"},
        {"label": "Template variables", "href": "/template-variables/"},
        {"label": "Image examples", "href": "/images/"},
        {"label": "Deploy dry-run", "href": "/deploy/"},
    ]


YAML_FUNCTIONS = {
    "demo_status": demo_status,
    "demo_build_label": demo_build_label,
    "demo_links": demo_links,
}
