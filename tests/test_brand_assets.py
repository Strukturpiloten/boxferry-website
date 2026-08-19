"""Tests for token-derived brand assets and accessibility boundaries."""

from __future__ import annotations

import unittest

from scripts.generate_brand_assets import (
    GENERATED_ASSET_PATHS,
    MARK_SOURCE,
    ROOT,
    TOKEN_FILE,
    WORDMARK_SOURCE,
    BrandAssetError,
    parse_palettes,
    render_assets,
)


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


class BrandAssetTests(unittest.TestCase):
    """Keep vector variants reproducible, safe, and legible."""

    def test_generated_assets_match_sources_and_tokens(self) -> None:
        expected = render_assets(ROOT)
        self.assertEqual(tuple(expected), GENERATED_ASSET_PATHS)
        for relative, content in expected.items():
            with self.subTest(asset=relative):
                actual = (ROOT / relative).read_text(encoding="utf-8")
                self.assertEqual(actual, content)
                self.assertIn("viewBox=", actual)
                self.assertIn("<title", actual)
                self.assertNotIn("<script", actual.casefold())
                self.assertNotIn("href=", actual.casefold())

    def test_monochrome_sources_have_no_embedded_color_or_remote_asset(self) -> None:
        for relative in (MARK_SOURCE, WORDMARK_SOURCE):
            source = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(source=relative):
                self.assertIn("currentColor", source)
                self.assertNotRegex(source, r"#[0-9a-fA-F]{3,8}\b")
                self.assertNotIn("href=", source.casefold())

    def test_missing_palette_fails_closed(self) -> None:
        with self.assertRaisesRegex(BrandAssetError, "missing dark color-scheme block"):
            parse_palettes("")

    def test_theme_contrast_meets_documented_targets(self) -> None:
        palettes = parse_palettes((ROOT / TOKEN_FILE).read_text(encoding="utf-8"))
        for name, palette in palettes.items():
            background = palette["--bf-background"]
            with self.subTest(theme=name, pair="body text"):
                self.assertGreaterEqual(_contrast(palette["--bf-text"], background), 7.0)
            with self.subTest(theme=name, pair="muted text"):
                self.assertGreaterEqual(_contrast(palette["--bf-text-muted"], background), 4.5)
            for token in (
                "--bf-brand-primary",
                "--bf-brand-secondary",
                "--bf-brand-accent",
                "--bf-info",
                "--bf-success",
                "--bf-warning",
                "--bf-error",
            ):
                with self.subTest(theme=name, token=token):
                    self.assertGreaterEqual(_contrast(palette[token], background), 4.5)
            with self.subTest(theme=name, pair="focus indicator"):
                self.assertGreaterEqual(_contrast(palette["--bf-focus"], background), 3.0)
            with self.subTest(theme=name, pair="primary button"):
                self.assertGreaterEqual(
                    _contrast(palette["--bf-on-brand"], palette["--bf-brand-primary-strong"]),
                    4.5,
                )


if __name__ == "__main__":
    unittest.main()
