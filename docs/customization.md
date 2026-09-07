# Customize the website

Presentation settings are intentionally split by responsibility.

| Change                                              | File                                                     |
| --------------------------------------------------- | -------------------------------------------------------- |
| Top navigation, feature flags, header logo, favicon | `zensical.toml`                                          |
| Content width, homepage layout, component styling   | `content/assets/stylesheets/site.css`                    |
| Dark and light color values, typography, spacing    | `content/assets/stylesheets/tokens.css`                  |
| BoxFerry mark and wordmark source vectors           | `content/assets/images/brand/`                           |
| GitHub and Strukturpiloten header icons             | `overrides/partials/source.html` and `overrides/.icons/` |

## Change the top navigation

Edit the `nav` array in `zensical.toml` to change the page hierarchy and labels. The `Docs`
and `Support` links displayed at the right of the header are rendered by
`overrides/partials/source.html`; their spacing and appearance use `.bf-header-links` and
`.bf-header-link--text` in `site.css`.

Keep `navigation.tabs` and `navigation.tabs.sticky` out of the theme `features` array. Those
features render top-level navigation in a separate row below the header instead of beside the
BoxFerry identity.

## Change the homepage and supported formats

`content/index.md` selects `overrides/home.html` and retains the command example. The homepage
template owns the introduction, format diagram, input-guide entries, and community section. It
inherits the normal theme header, search, and footer.

Edit `project.extra.formats` in `zensical.toml` to update the homepage's supported format set. Each
record has a stable `id`, public `label`, short `description`, and site-relative input `guide` ending
in `/`. One record renders one chip and one guide entry. CSS wraps both grids without a fixed count;
five or six formats do not need additional template branches or a list of every possible route.

Add a format only after its behavior and input guide are published. Update the owning product or
library documentation, source mappings, and navigation first, then add the format record. Run the
complete gate and check desktop and mobile rendering with longer labels. Keep planned formats and
uncertain roadmap items out of the public registry.

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
the favicon. `overrides/partials/logo.html` selects the generated mark for the active theme in the
header, drawer, and homepage diagram.

Review [`brand.md`](brand.md) before changing geometry, clear space, or minimum sizes.
