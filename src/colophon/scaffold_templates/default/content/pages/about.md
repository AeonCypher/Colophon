---
title: About
summary: A simple static page that demonstrates content/pages routing.
---

## Static page routing

This file is `content/pages/about.md`. Colophon removes the `pages` prefix, so it renders at `/about/`.

Nested pages work the same way. A file at `content/pages/docs/install.md` would render at `/docs/install/`.

## Markdown front matter

The YAML block at the top supplies `title` and `summary`. The Markdown body becomes the `article` template variable.

## Template used

Static pages default to the `static` template alias from `content/site.yaml`, which points to `templates/simple.html` in this scaffold.
