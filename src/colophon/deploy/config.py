"""Deploy configuration loading and normalization.

Raw deploy YAML flows through expression resolution, defaults, target validation,
step validation, and secret redaction before pipeline execution.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from colophon.errors import DeployConfigError
from colophon.expressions import resolve_yaml_expression_values
from colophon.models import ProjectPaths
from colophon.project import project_or_default
from colophon.utils import bool_value, copy_value, deep_merge, mapping_value, read_yaml


DEFAULT_DEPLOY_STEPS = [
    "preflight_build",
    "mastodon_post",
    "enable_comments",
    "build",
    "upload",
]


DEFAULT_DEPLOY_POST = {
    "select": "latest_published",
}


DEFAULT_DEPLOY_MASTODON = {
    "access_token": "",
    "post_text": "Hey, check out my new blog post. {{ post.summary }} {{ post.url }}",
}


DEFAULT_DEPLOY_TARGET = {
    "transport": "ftps",
    "host": "",
    "port": 0,
    "username": "",
    "password": "",
    "remote_path": "",
    "purge": True,
}


DEFAULT_DEPLOY = {
    "default_target": "production",
    "steps": DEFAULT_DEPLOY_STEPS,
    "post": DEFAULT_DEPLOY_POST,
    "mastodon": DEFAULT_DEPLOY_MASTODON,
    "targets": {},
}


DEFAULT_TRANSPORT_PORTS = {
    "ftp": 21,
    "ftps": 21,
    "sftp": 22,
    "sshfs": 22,
}


def normalize_deploy_steps(value: Any) -> list[str]:
    raw_steps = value if isinstance(value, list) else DEFAULT_DEPLOY_STEPS
    steps = [str(step).strip() for step in raw_steps if str(step).strip()]
    unknown = [step for step in steps if step not in DEFAULT_DEPLOY_STEPS]

    if unknown:
        raise DeployConfigError(f"unknown deploy step(s): {', '.join(unknown)}")

    return steps or copy_value(DEFAULT_DEPLOY_STEPS)


def normalize_deploy_target(raw_target: Any) -> dict[str, Any]:
    target = deep_merge(DEFAULT_DEPLOY_TARGET, mapping_value(raw_target))
    transport = str(target.get("transport") or DEFAULT_DEPLOY_TARGET["transport"]).lower()

    if transport not in DEFAULT_TRANSPORT_PORTS:
        raise DeployConfigError(f"unknown deploy transport {transport!r}")

    try:
        port = int(target.get("port") or DEFAULT_TRANSPORT_PORTS[transport])
    except (TypeError, ValueError) as exc:
        raise DeployConfigError(f"invalid deploy port {target.get('port')!r}") from exc

    normalized = deep_merge(
        target,
        {
            "transport": transport,
            "port": port,
            "host": str(target.get("host") or "").strip(),
            "username": str(target.get("username") or "").strip(),
            "password": str(target.get("password") or ""),
            "remote_path": str(target.get("remote_path") or "").strip(),
            "purge": bool_value(target.get("purge"), True),
        },
    )
    missing = [
        key
        for key in ("host", "username", "remote_path")
        if not str(normalized.get(key) or "").strip()
    ]

    if missing:
        raise DeployConfigError(f"deploy target missing required field(s): {', '.join(missing)}")

    return normalized


def normalize_deploy_config(raw_config: Any) -> dict[str, Any]:
    raw = mapping_value(raw_config)
    deploy = mapping_value(raw.get("deploy") if "deploy" in raw else raw)
    resolved = resolve_yaml_expression_values(deploy, path="deploy")
    base = deep_merge(
        DEFAULT_DEPLOY,
        {key: copy_value(value) for key, value in resolved.items() if key != "targets"},
    )
    targets = mapping_value(resolved.get("targets"))

    if not targets:
        raise DeployConfigError("deploy.targets must contain at least one target")

    normalized_targets = {
        str(name): normalize_deploy_target(target)
        for name, target in targets.items()
    }
    default_target = str(base.get("default_target") or DEFAULT_DEPLOY["default_target"])

    if default_target not in normalized_targets:
        raise DeployConfigError(f"default deploy target {default_target!r} is not configured")

    return deep_merge(
        base,
        {
            "default_target": default_target,
            "steps": normalize_deploy_steps(base.get("steps")),
            "post": deep_merge(DEFAULT_DEPLOY_POST, mapping_value(base.get("post"))),
            "mastodon": deep_merge(
                DEFAULT_DEPLOY_MASTODON,
                mapping_value(base.get("mastodon")),
            ),
            "targets": normalized_targets,
        },
    )


def load_deploy_config(
    config_path: Path | None = None,
    project: ProjectPaths | None = None,
) -> dict[str, Any]:
    resolved_project = project_or_default(project)
    path = resolved_project.deploy_config if config_path is None else config_path
    raw = read_yaml(path)

    if not raw:
        raise DeployConfigError(f"missing deploy config: {path}")

    return normalize_deploy_config(raw)


def redact_secrets(value: Any, parent_key: str = "") -> Any:
    secret_fragments = ("password", "token", "secret")

    if isinstance(value, Mapping):
        return {
            key: (
                "[redacted]"
                if any(fragment in str(key).lower() for fragment in secret_fragments)
                and item not in (None, "")
                else redact_secrets(item, str(key))
            )
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [redact_secrets(item, parent_key) for item in value]

    if isinstance(value, tuple):
        return tuple(redact_secrets(item, parent_key) for item in value)

    return copy_value(value)
