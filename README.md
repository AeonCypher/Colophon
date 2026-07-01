# Colophon

Colophon is a content-first static site generator for YAML, Markdown, Jinja templates, trusted local Python hooks, image derivatives, RSS, Mastodon-aware pages, and config-driven deploys.

Colophon publishes to PyPI as `colophon-site`. The Python package and primary CLI command remain `colophon`.

## Quickstart

Install Colophon:

```bash
python -m pip install colophon-site
```

For a source install, pin the matching GitHub release tag:

```bash
python -m pip install git+https://github.com/LibertAiTech/Colophon.git@v0.1.0
```

Create a starter site with the built-in scaffold, then build and serve that generated project:

```bash
colophon scaffold ./my-site
cd ./my-site
colophon build --config colophon.yml
colophon serve --config colophon.yml --watch --port 8000
```

The `colophon-site` CLI alias is also installed:

```bash
colophon-site build --config colophon.yml
```

SFTP deploy support is optional:

```bash
python -m pip install 'colophon-site[sftp]'
python -m pip install 'colophon-site[sftp] @ git+https://github.com/LibertAiTech/Colophon.git@v0.1.0'
```

## Why Use Colophon?

- Content-first authoring with Markdown, YAML pages, frontmatter, and Jinja templates.
- Strict builds that fail early for bad config, missing images, unknown hooks, and unsafe deploy targets.
- Trusted local Python hooks when static content needs computed values without a plugin system.
- Static output for cheap hosting, with deploy recipes for FTP, FTPS, SFTP, and SSHFS.
- Built-in support for image variants, archive/tag/feed pages, Mastodon comments, and Mastodon timelines.
- No frontend bundler by default.

## Documentation

- [CLI guide](https://github.com/LibertAiTech/Colophon/blob/v0.1.0/docs/cli.md): install variants, commands, common flags, JSON output, manifests, and dry-runs.
- [Authorship guide](https://github.com/LibertAiTech/Colophon/blob/v0.1.0/docs/authorship.md): Markdown, YAML pages, frontmatter, collections, YAML expressions, and author-facing Python hooks.
- [Site design guide](https://github.com/LibertAiTech/Colophon/blob/v0.1.0/docs/site-design.md): project layout, config, templates, routes, static assets, vendor assets, images, and template helpers.
- [Publishing guide](https://github.com/LibertAiTech/Colophon/blob/v0.1.0/docs/publishing.md): deploy config, provider recipes, Mastodon setup, feeds, archive/tag output, and repeatable builds.
- [Python API guide](https://github.com/LibertAiTech/Colophon/blob/v0.1.0/docs/python-api.md): embedded API, public facade, build results, manifests, deploy calls, and errors.
- [Template reference](https://github.com/LibertAiTech/Colophon/blob/v0.1.0/docs/template-reference.md): complete template globals, filters, object shapes, image fields, Mastodon fields, and stability notes.
- [Reference](https://github.com/LibertAiTech/Colophon/blob/v0.1.0/docs/reference.md): compatibility policy, config key reference, troubleshooting, release expectations, and support boundaries.
- [Changelog](https://github.com/LibertAiTech/Colophon/blob/v0.1.0/CHANGELOG.md): release notes and release checklist.
- [Contributing](https://github.com/LibertAiTech/Colophon/blob/v0.1.0/CONTRIBUTING.md): development setup, architecture, coding style, and tests.

## Development

Run commands from this repository root:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -v
PYTHONPATH=src .venv/bin/python -m colophon --help
```

The package uses a `src/` layout. During local development, either install the package into the environment or set `PYTHONPATH=src`.

## AI Usage
This application, including some parts of the code and documentation, were created with the assistance of AI tools.
