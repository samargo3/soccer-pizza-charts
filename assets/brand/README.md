# Argo FC Analytics — brand assets ("1b Broadsheet")

Instrument Serif (masthead) + Public Sans (supporting text), warm ink/cream palette.

## The mark
An abstract pizza chart — ten slices at varying radii inside a hairline ring,
with the tallest slice in brick red: "the standout percentile." Rendered
deterministically from a fixed radius sequence in `build_assets.py`.

## Draft palette (sync with config/theme.json before final use)
- ink    #221C17
- paper  #F4EDDF
- accent #A8402A
- ochre  #C09035  (reserved, unused in these assets)
- muted  #8A7E6F

## Files
- mark-{dark,light}.{svg,png} — standalone mark (transparent)
- wordmark-{dark,light}, wordmark-compact-* — masthead type only
- lockup-{dark,light} — mark + masthead
- favicon.svg, favicon-32.png, apple-touch-icon.png, icon-512.png
- og-card.png — 1200x630 social card

SVG text is converted to paths — no font installs needed anywhere they're used.

## Regenerating
Edit PALETTE (and radii/type sizes if desired) in `build_assets.py`, then:
`python build_assets.py` (needs matplotlib + the two font files in ./fonts).
