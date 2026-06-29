"""Mastodon site, timeline, and comment normalization.

Raw site/page Mastodon settings flow into template-ready timeline options and
comment thread metadata shared by content rendering and deploy write-back.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from .utils import bool_value, copy_value, deep_merge, mapping_value, trim_url


DEFAULT_MASTODON_TIMELINE = {
    "enabled": False,
    "mtContainerId": "mastodon-timeline",
    "instanceUrl": "",
    "timelineType": "profile",
    "userId": "",
    "profileName": "",
    "defaultTheme": "dark",
    "maxNbPostFetch": "20",
    "maxNbPostShow": "5",
    "hideReblog": True,
    "hideReplies": True,
}


DEFAULT_MASTODON_COMMENTS = {
    "enabled": False,
    "host": "",
    "user": "",
    "toot_id": "",
    "filter": "",
    "lang": "",
}


DEFAULT_MASTODON = {
    "enabled": False,
    "host": "",
    "instance_url": "",
    "user": "",
    "user_id": "",
    "profile_name": "",
    "timeline": DEFAULT_MASTODON_TIMELINE,
}


PLACEHOLDER_MASTODON_HOSTS = {"mastodon.example"}


def normalize_mastodon_host(value: Any) -> str:
    text = trim_url(value)

    if not text:
        return ""

    parsed = urlparse(text if "://" in text else f"https://{text}")
    return (parsed.netloc or parsed.path).strip("/")


def normalize_mastodon_instance_url(value: Any) -> str:
    text = trim_url(value)

    if not text:
        return ""

    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = parsed.netloc or parsed.path
    return f"{parsed.scheme or 'https'}://{host.strip('/')}"


def mastodon_instance_url_from_config(config: Mapping[str, Any]) -> str:
    host = normalize_mastodon_host(config.get("host"))
    instance_host = normalize_mastodon_host(config.get("instance_url"))

    if host and instance_host in PLACEHOLDER_MASTODON_HOSTS:
        return normalize_mastodon_instance_url(host)

    return normalize_mastodon_instance_url(config.get("instance_url") or host)


def parse_mastodon_status_url(value: Any) -> dict[str, str]:
    text = trim_url(value)

    if not text:
        return {}

    parsed = urlparse(text if "://" in text else f"https://{text}")
    parts = [part for part in parsed.path.split("/") if part]

    if len(parts) >= 2 and parts[0].startswith("@"):
        return {
            "host": normalize_mastodon_host(parsed.netloc),
            "user": parts[0].lstrip("@").split("@")[0],
            "toot_id": parts[1],
        }

    if len(parts) >= 4 and parts[0] == "users" and parts[2] == "statuses":
        return {
            "host": normalize_mastodon_host(parsed.netloc),
            "user": parts[1],
            "toot_id": parts[3],
        }

    return {}


def normalize_mastodon_timeline(
    mastodon: Mapping[str, Any],
    timeline_config: Any = None,
) -> dict[str, Any]:
    raw = mapping_value(
        timeline_config if timeline_config is not None else mastodon.get("timeline")
    )
    inline_options = {
        key: copy_value(value)
        for key, value in raw.items()
        if key not in {"enabled", "options"}
    }
    explicit_options = mapping_value(raw.get("options"))
    instance_url = normalize_mastodon_instance_url(
        mastodon.get("instance_url") or mastodon.get("host")
    )
    defaults = deep_merge(
        DEFAULT_MASTODON_TIMELINE,
        {
            "instanceUrl": instance_url,
            "userId": str(mastodon.get("user_id") or ""),
            "profileName": str(mastodon.get("profile_name") or ""),
        },
    )
    options = deep_merge(defaults, deep_merge(inline_options, explicit_options))
    timeline_options = {
        key: value
        for key, value in options.items()
        if key != "enabled"
    }

    return {
        "enabled": bool_value(raw.get("enabled"), bool_value(mastodon.get("enabled"))),
        "container_id": str(
            timeline_options.get("mtContainerId") or DEFAULT_MASTODON_TIMELINE["mtContainerId"]
        ),
        "options": timeline_options,
    }


def normalize_mastodon_comment_defaults(mastodon: Mapping[str, Any]) -> dict[str, Any]:
    return deep_merge(
        DEFAULT_MASTODON_COMMENTS,
        {
            "host": normalize_mastodon_host(
                mastodon.get("host") or mastodon.get("instance_url")
            ),
            "user": str(mastodon.get("user") or ""),
        },
    )


def normalize_mastodon_site_config(raw_config: Any) -> dict[str, Any]:
    raw = mapping_value(raw_config)
    config = {
        key: value
        for key, value in deep_merge(DEFAULT_MASTODON, raw).items()
        if key != "comments"
    }
    host = normalize_mastodon_host(config.get("host") or config.get("instance_url"))
    instance_url = mastodon_instance_url_from_config(config)
    mastodon = deep_merge(
        config,
        {
            "enabled": bool_value(config.get("enabled")),
            "host": host,
            "instance_url": instance_url,
        },
    )

    return deep_merge(
        mastodon,
        {
            "timeline": normalize_mastodon_timeline(
                mastodon,
                mapping_value(raw.get("timeline")),
            ),
        },
    )


def normalize_mastodon_comments(
    raw_config: Any,
    site_mastodon: Mapping[str, Any],
) -> dict[str, Any]:
    raw = {"status_url": raw_config} if isinstance(raw_config, str) else mapping_value(raw_config)
    defaults = normalize_mastodon_comment_defaults(site_mastodon)
    from_status_url = parse_mastodon_status_url(raw.get("status_url"))
    explicit = {
        key: copy_value(value)
        for key, value in raw.items()
        if key not in {"enabled", "status_url"}
    }
    merged = deep_merge(deep_merge(defaults, from_status_url), explicit)
    merged = deep_merge(
        merged,
        {
            "host": normalize_mastodon_host(merged.get("host")),
            "user": str(merged.get("user") or ""),
            "toot_id": str(merged.get("toot_id") or merged.get("tootId") or ""),
        },
    )
    has_thread = all(merged.get(key) for key in ("host", "user", "toot_id"))
    default_enabled = bool_value(defaults.get("enabled"))
    explicit_enabled = bool_value(raw.get("enabled"), default=bool(raw) or default_enabled)

    return deep_merge(
        merged,
        {"enabled": has_thread and explicit_enabled},
    )
