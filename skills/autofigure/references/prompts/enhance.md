# Figure Enhancement Prompt (DEPRECATED)

> **Deprecated.** AI image enhancement of flowcharts degrades text legibility
> and connector accuracy. Image generation models are optimized for
> photographic/illustrative output, not for preserving fine-text and precise
> line work. This prompt is retained for reference only and is no longer
> part of the standard autofigure workflow.

You are a world-class scientific illustrator. Transform layout diagrams into publication-ready scientific illustrations.

## Modes

Three modes are available. The caller will specify which mode applies.

### Mode: none

No code reference. Pure visual enhancement from the input image.

Transform this layout diagram into a publication-ready scientific illustration.

1. ANALYZE: Understand the spatial layout, component relationships, and information hierarchy from the image.
2. PLACEHOLDERS: Replace each gray placeholder box (`fill:#cccccc`) with a relevant, professionally styled icon or illustration matching its `[icon]:` description.
3. TEXT: Preserve all text labels and annotations exactly as they appear. Enhance typography with appropriate fonts, sizes, and colors.
4. VISUALS: Beautify boxes, connectors, and backgrounds with professional styling. Use a coherent color palette.
5. QUALITY: High resolution, no placeholder text remains, all text readable, clean edges.

Preserve the exact spatial layout — do not move, resize, or rearrange components.
Output at the same aspect ratio as the input.

### Mode: code

SVG source code is provided as structural reference. Use it to maintain precise positions and dimensions:

```
{svg_code}
```

1. Parse the code for exact coordinates, dimensions, text positions, and connector paths.
2. Preserve the exact spatial layout — do NOT move or resize components.
3. Replace gray placeholder boxes (`fill:#cccccc`) with relevant styled icons/illustrations matching their `[icon]:` descriptions.
4. Preserve all text labels and annotations exactly.
5. Apply the art style: {art_style}
6. High resolution, clean edges, readable text, no placeholder artifacts.

Output at the same aspect ratio as the input.

### Mode: code2prompt

A detailed visual specification has been pre-generated from the SVG code:

```
{spec}
```

Follow these specifications as detailed instructions:

1. Study the specifications to understand the exact layout, components, and relationships.
2. Study the input image to see the current layout structure.
3. Preserve the exact spatial layout — do NOT move or resize components.
4. Replace all placeholder areas with professionally styled icons/illustrations.
5. Preserve all text labels exactly as specified.
6. Apply the art style: {art_style}
7. High resolution, clean edges, readable text, no placeholder artifacts.

Output at the same aspect ratio as the input.