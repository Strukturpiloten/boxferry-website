# Customize the website

Presentation settings are intentionally split by responsibility.

| Change                                              | File                                                     |
| --------------------------------------------------- | -------------------------------------------------------- |
| Top navigation, feature flags, header logo, favicon | `zensical.toml`                                          |
| Content width, homepage layout, component styling   | `content/assets/stylesheets/site.css`                    |
| Dark and light color values, typography, spacing    | `content/assets/stylesheets/tokens.css`                  |
| BoxFerry mark and wordmark source vectors           | `content/assets/images/brand/`                           |
| GitHub and Strukturpiloten header icons             | `overrides/partials/source.html` and `overrides/.icons/` |

## Change the content width

Edit the `.md-grid` rule near the top of `site.css`. Its `max-width` controls the shared page grid;
responsive sidebars and the main content column continue to use Zensical's layout.

## Change colors

Edit only literal colors in `tokens.css`, under the `slate` dark scheme and `default` light scheme.
Do not place a literal production color in `site.css` or an authored logo variant. Run the brand
generator after changing a brand color:

```console
uv run --frozen python scripts/generate_brand_assets.py
```

The complete check verifies contrast and rejects stale generated assets.

## Change the logo

Edit the monochrome source SVGs in `content/assets/images/brand/`, then run the generator. Generated
dark, light, favicon, and social-preview assets must not be edited by hand. `zensical.toml` selects
the header logo and favicon; `content/index.md` selects the homepage wordmark.

Review [`brand.md`](brand.md) before changing geometry, clear space, or minimum sizes.
