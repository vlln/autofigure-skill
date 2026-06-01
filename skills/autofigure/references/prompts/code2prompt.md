# Code-to-Prompt Conversion (DEPRECATED)

> **Deprecated.** This prompt converts SVG code to text-to-image specifications
> for AI image enhancement — a step that has been removed from the standard
> workflow. Retained for reference only.

You are a scientific illustration specification writer. Convert the following figure code into a comprehensive, detailed text-to-image prompt that an image generation model can use to create a beautiful, publication-ready illustration.

## Figure Code
```svg
{svg_code}
```

## Art Style
{art_style}

## Requirements
Describe every visual element in precise detail:
1. Overall layout structure (positions, sizes, spatial relationships of all components)
2. Each box/container: its position, size, color, border style, and content
3. All text labels: exact text, position, font size, color, and alignment
4. All connectors/arrows: direction, style, endpoints, and labels
5. Placeholder areas (gray boxes with fill:#cccccc): describe what icon or illustration should replace each placeholder, based on its [icon]: description
6. Color palette: list every color used and where
7. Typography hierarchy: font sizes, weights, and styles organized by importance

Output a single, flowing description paragraph (not a JSON, not a list). Make it detailed enough that an illustrator could recreate the figure exactly. Focus on visual specifics, not abstract concepts.