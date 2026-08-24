# BoxFerry visual identity

BoxFerry uses a restrained infrastructure identity that must remain legible in technical
documentation, command-line examples, small navigation controls, and social previews.

## Design principles

- Show N:N movement without implying one privileged conversion direction.
- Combine container structure and ferry transport without drawing a detailed illustration.
- Prefer simple geometry that remains recognizable at 16 pixels.
- Keep production colors derived from the central design-token stylesheet.
- Use local system typography; do not require a remote font or browser-side dependency.

## Evaluated directions

| Direction   | Preview                                          | Evaluation                                                                                                               |
| ----------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| Cargo route | [Vector concept](brand-concepts/cargo-route.svg) | Selected. Four endpoints and crossing routes communicate N:N conversion inside a container carried by a simplified hull. |
| Ferry wake  | [Vector concept](brand-concepts/ferry-wake.svg)  | Strong transport metaphor, but does not communicate format conversion clearly enough.                                    |
| BF monogram | [Vector concept](brand-concepts/bf-monogram.svg) | Compact and readable, but less distinctive and too dependent on knowing the product name.                                |

The cargo-route direction is the production identity. Its crossing lines describe independent
input-to-output routes rather than a synchronization symbol or one-way migration arrow.

## Production assets

The monochrome originals are:

- `content/assets/images/brand/boxferry-mark.svg` for compact contexts;
- `content/assets/images/brand/boxferry-wordmark.svg` for product lockups.

The mark should not render below 16 pixels. The wordmark should not render below 120 pixels wide.
Keep clear space around either asset equal to at least one endpoint circle in the compact mark.

`scripts/generate_brand_assets.py` creates dark, light, favicon, and social-preview SVG variants.
It reads every production color from `content/assets/stylesheets/tokens.css`. Generated variants are
committed so browsers and external consumers can use them directly, but the complete check rejects
manual or stale changes.

Run the generator directly only when reviewing brand assets:

```console
uv run --frozen python scripts/generate_brand_assets.py
uv run --frozen python scripts/generate_brand_assets.py --check
```

The normal complete repository task already generates or checks these files.

## Company mark

The header uses `overrides/.icons/strukturpiloten/rocket.svg`, a compact monochrome reconstruction
of the Strukturpiloten favicon. It is a separate company mark rather than part of the BoxFerry logo
system. Keeping it inline and colored with `currentColor` avoids a remote request and preserves
legibility in both site themes.

## Design tokens

`tokens.css` is the only source for literal production colors. It also defines system-font stacks,
type scale, spacing, radius, shadow, icon-size, motion-duration, and easing tokens. Site styles use
those tokens rather than maintaining a second design system.

For the exact navigation, content-width, color, and logo entry points, use
[`customization.md`](customization.md).

Dark mode is the first-visit default. Light mode remains explicitly selectable. The maintained
contrast contract is:

- body text against the page background: at least 7:1;
- normal muted, brand, and diagnostic text: at least 4.5:1;
- primary-button text: at least 4.5:1;
- focus indicators: at least 3:1 against the page background.

Automated tests verify these pairs. The site additionally respects reduced-motion and
increased-contrast preferences, retains visible keyboard focus, and uses responsive layouts.

## Usage boundaries

- Do not recolor production SVGs manually; change `tokens.css` and regenerate them.
- Do not stretch, rotate, outline, shadow, or rearrange the mark.
- Do not replace the system wordmark typography with a remotely hosted font.
- Do not use a directional arrow that suggests BoxFerry supports only one source-to-target route.
- Do not place secrets, environment values, or user input in social-preview assets.
