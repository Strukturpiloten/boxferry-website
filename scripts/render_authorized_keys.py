#!/usr/bin/env python3
"""Render copy-ready restricted Hetzner authorized_keys entries."""

from __future__ import annotations

import argparse
import base64
import binascii
import re
import sys
from pathlib import Path

DEPLOYMENT_ROOT_PATTERN = re.compile(r"/(?:[A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+")
PUBLIC_KEY_PATTERN = re.compile(r"ssh-ed25519 ([A-Za-z0-9+/]+={0,3})(?:[ \t]+[^\r\n]+)?")


class AuthorizedKeysError(RuntimeError):
    """Describe unsafe deployment-key input."""


def validate_deployment_root(value: str) -> str:
    """Accept only an absolute path without shell syntax or traversal."""
    if not DEPLOYMENT_ROOT_PATTERN.fullmatch(value) or ".." in Path(value).parts:
        raise AuthorizedKeysError("deployment root must be a safe absolute POSIX path")
    return value.rstrip("/")


def normalize_public_key(value: str) -> str:
    """Validate one Ed25519 public key and discard its untrusted comment."""
    match = PUBLIC_KEY_PATTERN.fullmatch(value)
    if match is None:
        raise AuthorizedKeysError("public key must contain exactly one ssh-ed25519 key")
    try:
        decoded = base64.b64decode(match.group(1), validate=True)
    except (binascii.Error, ValueError) as error:
        raise AuthorizedKeysError("public key contains invalid base64") from error
    if len(decoded) < 32:
        raise AuthorizedKeysError("public key payload is unexpectedly short")
    return f"ssh-ed25519 {match.group(1)}"


def read_public_key(path: Path) -> str:
    """Read and structurally validate one Ed25519 public key."""
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise AuthorizedKeysError(f"cannot read public key: {path}") from error
    return normalize_public_key(value)


def render_authorized_keys(
    deployment_root: str,
    rsync_public_key: str,
    updater_public_key: str,
) -> tuple[str, str]:
    """Return the rsync-only and updater-only authorized_keys entries."""
    rsync_public_key = normalize_public_key(rsync_public_key)
    updater_public_key = normalize_public_key(updater_public_key)
    root = validate_deployment_root(deployment_root)

    upload_command = f"/usr/bin/rrsync -wo {root}/incoming"
    updater_command = (
        f"/usr/bin/flock -n {root}/.deploy/version-updater.lock {root}/.deploy/version-updater.sh"
    )
    return (
        f'restrict,command="{upload_command}" {rsync_public_key} boxferry-website-rsync',
        f'restrict,command="{updater_command}" {updater_public_key} '
        "boxferry-website-version-updater",
    )


def main() -> int:
    """Render both entries from public-key files derived by ssh-keygen."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment-root", required=True)
    parser.add_argument("--rsync-public-key", required=True, type=Path)
    parser.add_argument("--updater-public-key", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        lines = render_authorized_keys(
            arguments.deployment_root,
            read_public_key(arguments.rsync_public_key),
            read_public_key(arguments.updater_public_key),
        )
    except AuthorizedKeysError as error:
        print(f"boxferry-website: authorized_keys rendering failed: {error}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
