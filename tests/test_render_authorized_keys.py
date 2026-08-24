"""Tests for least-privilege deployment key entries."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.render_authorized_keys import (
    AuthorizedKeysError,
    read_public_key,
    render_authorized_keys,
    validate_deployment_root,
)

ROOT = "/usr/www/users/c3diiy/dev_boxferry"
PUBLIC_KEY = "ssh-ed25519 " + "QUFB" * 12


class AuthorizedKeysTests(unittest.TestCase):
    """Reject command injection and render exact forced commands."""

    def test_rendered_entries_are_copy_ready_and_separated(self) -> None:
        upload, updater = render_authorized_keys(ROOT, PUBLIC_KEY, PUBLIC_KEY)

        self.assertEqual(
            upload,
            'restrict,command="/usr/bin/rrsync -wo '
            f'{ROOT}/incoming" {PUBLIC_KEY} boxferry-website-rsync',
        )
        self.assertEqual(
            updater,
            'restrict,command="/usr/bin/flock -n '
            f'{ROOT}/.deploy/version-updater.lock {ROOT}/.deploy/version-updater.sh" '
            f"{PUBLIC_KEY} boxferry-website-version-updater",
        )

    def test_unsafe_deployment_roots_are_rejected(self) -> None:
        for value in (
            "relative/path",
            "/usr/www/../etc",
            "/usr/www/site;id",
            "/usr/www/site with space",
            '/usr/www/site"',
        ):
            with self.subTest(value=value), self.assertRaises(AuthorizedKeysError):
                validate_deployment_root(value)

    def test_non_ed25519_or_commented_key_is_rejected(self) -> None:
        for value in (
            "ssh-rsa " + "QUFB" * 12,
            PUBLIC_KEY + " unexpected-comment",
            "ssh-ed25519 not-base64!",
        ):
            with self.subTest(value=value), self.assertRaises(AuthorizedKeysError):
                render_authorized_keys(ROOT, value, PUBLIC_KEY)

    def test_public_key_file_must_contain_one_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key.pub"
            path.write_text(PUBLIC_KEY + "\n" + PUBLIC_KEY + "\n", encoding="utf-8")

            with self.assertRaisesRegex(AuthorizedKeysError, "exactly one"):
                read_public_key(path)


if __name__ == "__main__":
    unittest.main()
