"""Tests for least-privilege deployment key entries."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.render_authorized_keys import (
    AuthorizedKeysError,
    normalize_public_key,
    read_public_key,
    render_authorized_keys,
    validate_deployment_root,
)

ROOT = "/srv/boxferry-test/deployment"
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
            "/srv/boxferry/../etc",
            "/srv/boxferry;id",
            "/srv/boxferry with space",
            '/srv/boxferry"',
        ):
            with self.subTest(value=value), self.assertRaises(AuthorizedKeysError):
                validate_deployment_root(value)

    def test_public_key_comments_are_discarded(self) -> None:
        commented_key = PUBLIC_KEY + " key comment with spaces"

        self.assertEqual(normalize_public_key(commented_key), PUBLIC_KEY)
        upload, updater = render_authorized_keys(ROOT, commented_key, commented_key)
        self.assertNotIn("key comment with spaces", upload)
        self.assertNotIn("key comment with spaces", updater)
        self.assertIn(f"{PUBLIC_KEY} boxferry-website-rsync", upload)
        self.assertIn(f"{PUBLIC_KEY} boxferry-website-version-updater", updater)

    def test_non_ed25519_or_invalid_key_is_rejected(self) -> None:
        for value in (
            "ssh-rsa " + "QUFB" * 12,
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

    def test_public_key_file_comment_is_discarded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key.pub"
            path.write_text(PUBLIC_KEY + " generated-key-comment\n", encoding="utf-8")

            self.assertEqual(read_public_key(path), PUBLIC_KEY)


if __name__ == "__main__":
    unittest.main()
