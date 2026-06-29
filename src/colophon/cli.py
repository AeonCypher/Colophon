"""Command-line parsing and dispatch for Colophon.

Arguments are normalized into a ``ProjectPaths`` value, then routed to build,
serve, deploy, or scaffold subsystems without owning their implementation.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from .build import build_site, resolve_required_vendor_assets
from .deploy.pipeline import deploy_site
from .models import ProjectPaths
from .project import DEFAULT_CONFIG_FILE, absolute_project_path, conventional_project, legacy_project, project_from_config
from .scaffold import scaffold_site
from .serve import serve_site
from .vendor import download_vendor_assets


def add_project_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE, help="Path to colophon.yml.")
    parser.add_argument("--content", help="Override the configured content directory.")
    parser.add_argument("--templates", help="Override the configured templates directory.")
    parser.add_argument("--static", help="Override the configured static directory.")
    parser.add_argument("--output", help="Override the configured output directory.")


def project_from_args(args: argparse.Namespace) -> ProjectPaths:
    config = Path(args.config)

    if config.exists() or args.config != DEFAULT_CONFIG_FILE:
        return project_from_config(
            config,
            content=args.content,
            templates=args.templates,
            static=args.static,
            output=args.output,
        )

    conventional = conventional_project(Path.cwd())
    content_dir = absolute_project_path(conventional.root, args.content, "content")
    templates_dir = absolute_project_path(conventional.root, args.templates, "templates")
    static_dir = absolute_project_path(conventional.root, args.static, "static")
    output_dir = absolute_project_path(conventional.root, args.output, "_site")

    return replace(
        conventional,
        content_dir=content_dir,
        posts_dir=content_dir / "posts",
        content_images_dir=content_dir / "images",
        templates_dir=templates_dir,
        static_dir=static_dir,
        output_dir=output_dir,
        deploy_config=content_dir / "deploy.yaml",
        site_configs=(content_dir / "site.yaml", content_dir / "site.yml"),
        image_configs=(content_dir / "images.yaml", content_dir / "images.yml"),
        post_sidebar_configs=(content_dir / "post-sidebar.yaml", content_dir / "post-sidebar.yml"),
        watched_dirs=(content_dir, templates_dir, static_dir),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="colophon")
    subparsers = parser.add_subparsers(dest="command")

    build = subparsers.add_parser("build", help="Build the static site.")
    add_project_arguments(build)

    serve = subparsers.add_parser("serve", help="Build and serve the static site.")
    add_project_arguments(serve)
    serve.add_argument("--watch", action="store_true", help="Rebuild on file changes.")
    serve.add_argument("--test", action="store_true", help="Serve briefly, then stop.")
    serve.add_argument("--port", type=int, default=8000)

    deploy = subparsers.add_parser("deploy", help="Build, announce, and upload the site.")
    add_project_arguments(deploy)
    deploy.add_argument("--target", help="Deploy target name from deploy config.")
    deploy.add_argument("--post-id", help="Post slug to announce instead of the configured selector.")
    deploy.add_argument("--dry-run", action="store_true", help="Show deploy actions without posting or uploading.")
    deploy.add_argument("--force-post", action="store_true", help="Create a new Mastodon post even when one is already linked.")

    scaffold = subparsers.add_parser("scaffold", help="Create a boring demo site.")
    scaffold.add_argument("path", help="Directory to create.")
    scaffold.add_argument("--force", action="store_true", help="Allow scaffolding into an existing empty directory.")
    scaffold_source = scaffold.add_mutually_exclusive_group()
    scaffold_source.add_argument("--template", default="default", help="Packaged scaffold template name.")
    scaffold_source.add_argument("--template-dir", help="Local scaffold template directory containing colophon.yml.")

    vendor = subparsers.add_parser("vendor", help="Manage browser vendor assets.")
    vendor_subparsers = vendor.add_subparsers(dest="vendor_command")
    vendor_download = vendor_subparsers.add_parser("download", help="Download browser vendor assets locally.")
    add_project_arguments(vendor_download)
    vendor_download.add_argument("--asset", action="append", default=[], help="Vendor asset name to download.")
    vendor_download.add_argument("--force", action="store_true", help="Overwrite existing local vendor files.")
    vendor_download.add_argument("--dry-run", action="store_true", help="Show planned downloads without writing files.")

    add_project_arguments(parser)
    parser.add_argument("--deploy", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--target", help=argparse.SUPPRESS)
    parser.add_argument("--post-id", help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--force-post", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--watch", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8000, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scaffold":
        scaffold_site(
            Path(args.path),
            force=args.force,
            template=args.template,
            template_dir=Path(args.template_dir) if args.template_dir else None,
        )
        return

    if args.command == "vendor":
        if args.vendor_command != "download":
            parser.error("vendor requires a subcommand")

        project = project_from_args(args)
        names = tuple(args.asset) or resolve_required_vendor_assets(project)
        for action in download_vendor_assets(
            project,
            names,
            force=args.force,
            dry_run=args.dry_run,
        ):
            print(action)
        return

    legacy_flag_mode = args.command is None and any(
        [args.deploy, args.serve, args.watch, args.test]
    )
    project = (
        legacy_project()
        if legacy_flag_mode and args.config == DEFAULT_CONFIG_FILE
        else project_from_args(args)
    )

    if args.command == "deploy" or args.deploy:
        deploy_site(
            project=project,
            target=args.target,
            post_id=args.post_id,
            dry_run=args.dry_run,
            force_post=args.force_post,
        )
        return

    build_site(project)

    if args.command == "serve" or args.serve or args.watch or args.test:
        serve_site(
            args.port,
            project=project,
            watch=args.watch,
            test=args.test,
        )
