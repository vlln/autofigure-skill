#!/usr/bin/env python3
"""Image enhancement for scientific figures via image generation APIs.

Converts a layout PNG (and optionally SVG code) into a visually polished,
publication-ready illustration using an image generation model.

Modes:
  none        — Direct visual enhancement, no code reference
  code        — Pass SVG code as structural reference
  code2prompt — Convert SVG code to a detailed text2image prompt via LLM first (default)

Usage:
  python enhance.py <layout.png> --svg <figure.svg> [--mode code2prompt] [--style "..."]
  python enhance.py <layout.png> --mode none
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_config() -> dict:
    c2p_key = _env("AUTOFIGURE_CODE2PROMPT_API_KEY") or _env("AUTOFIGURE_EVAL_API_KEY")
    c2p_model = _env("AUTOFIGURE_CODE2PROMPT_MODEL") or _env("AUTOFIGURE_EVAL_MODEL", "google/gemini-2.5-flash")
    return {
        "enhance_api_key": _env("AUTOFIGURE_ENHANCE_API_KEY"),
        "enhance_base_url": _env("AUTOFIGURE_ENHANCE_BASE_URL", "https://openrouter.ai/api/v1"),
        "enhance_model": _env("AUTOFIGURE_ENHANCE_MODEL", "google/gemini-2.5-flash-image"),
        "enhance_provider": _env("AUTOFIGURE_ENHANCE_PROVIDER", "openai"),
        "enhance_input_type": _env("AUTOFIGURE_ENHANCE_INPUT_TYPE", "code2prompt"),
        "art_style": _env("AUTOFIGURE_ART_STYLE", "Modern scientific illustration"),
        "code2prompt_api_key": c2p_key,
        "code2prompt_base_url": _env("AUTOFIGURE_CODE2PROMPT_BASE_URL", "https://openrouter.ai/api/v1"),
        "code2prompt_model": c2p_model,
    }


# ── code2prompt: SVG code → text2image description ──────────────────────────

CODE2PROMPT_TEMPLATE = """You are a scientific illustration specification writer. Convert the following figure code into a comprehensive, detailed text-to-image prompt that an image generation model can use to create a beautiful, publication-ready illustration.

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
5. Placeholder areas (gray boxes): describe what icon or illustration should replace each placeholder
6. Color palette: list every color used and where
7. Typography hierarchy: font sizes, weights, and styles organized by importance

Output a single, flowing description paragraph (not a JSON, not a list). Make it detailed enough that an illustrator could recreate the figure exactly. Focus on visual specifics, not abstract concepts."""


def _code_to_prompt(svg_code: str, art_style: str, config: dict) -> str | None:
    """Convert SVG code to a detailed text2image prompt via LLM."""
    import urllib.request
    import urllib.error

    api_key = config["code2prompt_api_key"]
    if not api_key:
        return None

    prompt = CODE2PROMPT_TEMPLATE.format(
        svg_code=svg_code[:8000], art_style=art_style
    )

    body = {
        "model": config["code2prompt_model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    url = f"{config['code2prompt_base_url']}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"code2prompt LLM call failed: {e}", file=sys.stderr)
        return None


# ── Enhancement prompt builders ─────────────────────────────────────────────

def _build_prompt_none() -> str:
    return """You are a world-class scientific illustrator. Transform this layout diagram into a publication-ready scientific illustration.

The input is a diagram with labeled boxes, connectors, and placeholder areas (gray boxes containing [icon]: descriptions). Your task is to enhance it while preserving the exact layout structure:

1. ANALYZE: Understand the spatial layout, component relationships, and information hierarchy.
2. PLACEHOLDERS: Replace each gray placeholder box with a relevant, professionally styled icon or illustration matching its [icon]: description.
3. TEXT: Preserve all text labels and annotations exactly as they appear. Enhance typography with appropriate fonts, sizes, and colors.
4. VISUALS: Beautify boxes, connectors, and backgrounds with professional styling. Use a coherent color palette.
5. QUALITY: High resolution, no placeholder text remains, all text readable, clean edges.

Preserve the exact spatial layout — do not move, resize, or rearrange components."""


def _build_prompt_code(svg_code: str, art_style: str) -> str:
    return f"""You are a world-class scientific illustrator. Transform this layout diagram into a publication-ready scientific illustration.

The input is a diagram with labeled boxes, connectors, and placeholder areas. Below is the source code defining the exact layout. Use it as your structural reference — maintain precise positions and dimensions.

## Source Code (structural reference)
```svg
{svg_code[:5000]}
```

## Art Style
{art_style}

## Instructions
1. Parse the code for exact coordinates, dimensions, text positions, and connector paths.
2. Preserve the exact spatial layout — do NOT move or resize components.
3. Replace gray placeholder boxes with relevant styled icons/illustrations.
4. Preserve all text labels and annotations exactly.
5. Apply the art style consistently across all visual elements.
6. High resolution, clean edges, readable text, no placeholder artifacts.

Output the enhanced illustration at the same aspect ratio as the input."""


def _build_prompt_code2prompt(spec: str, art_style: str) -> str:
    return f"""You are a world-class scientific illustrator. Transform this layout diagram into a publication-ready scientific illustration.

## Art Style
{art_style}

## Comprehensive Visual Specifications
Follow these detailed requirements for creating the enhanced illustration:

{spec}

## Execution
1. Study the specifications to understand the exact layout, components, and relationships.
2. Study the input image to see the current layout structure.
3. Preserve the exact spatial layout — do NOT move or resize components.
4. Replace all placeholder areas with professionally styled icons/illustrations.
5. Preserve all text labels exactly as specified.
6. Apply the art style consistently across all elements.
7. High resolution, clean edges, readable text, no placeholder artifacts.

Output the enhanced illustration at the same aspect ratio as the input."""


# ── API callers ─────────────────────────────────────────────────────────────

def _encode_image(path: str) -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mime = mime_map.get(suffix, "image/png")
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def _enhance_openai(
    image_path: str, prompt: str, config: dict, output_path: str
) -> bool:
    """Enhance via OpenAI-compatible image generation API.

    Returns:
        True if image was extracted and saved to output_path.
        False if the API returned an async task (task_id printed to stdout)
        or if an error occurred.
    """
    import urllib.request
    import urllib.error

    image_b64 = _encode_image(image_path)
    mime = "image/png"

    body = {
        "model": config["enhance_model"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                    },
                ],
            }
        ],
        "modalities": ["image", "text"],
        "temperature": 0.7,
    }

    url = f"{config['enhance_base_url']}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['enhance_api_key']}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        # Check for DashScope async response (task_id in output)
        output = result.get("output", {})
        task_id = output.get("task_id")
        if task_id:
            task_status = output.get("task_status", "UNKNOWN")
            task_info = {
                "task_id": task_id,
                "task_status": task_status,
                "note": "Poll GET /api/v1/tasks/{task_id} to check status. "
                        "On SUCCEEDED, the image URL is in "
                        "output.choices[0].message.content[0].image.",
            }
            print(json.dumps(task_info))
            return False

        return _extract_image_openai(result, output_path)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")[:500]
        print(f"Enhancement API error (HTTP {e.code}): {error_body}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Enhancement failed: {e}", file=sys.stderr)
        return False


def _extract_image_openai(result: dict, output_path: str) -> bool:
    """Extract image from OpenAI-compatible response. Returns True on success."""
    choice = result.get("choices", [{}])[0]
    message = choice.get("message", {})

    # 1. OpenRouter-style: message.images array
    images = message.get("images", [])
    if images:
        img = images[0]
        if isinstance(img, dict) and "image_url" in img:
            url = img["image_url"].get("url", "")
        elif isinstance(img, str):
            url = img
        else:
            url = ""
        if url.startswith("data:image"):
            b64_data = url.split(",", 1)[1]
            Path(output_path).write_bytes(base64.b64decode(b64_data))
            return True

    # 2. Base64 in markdown content
    content = message.get("content", "")
    if isinstance(content, str):
        import re
        match = re.search(r"data:image/\w+;base64,([A-Za-z0-9+/=]+)", content)
        if match:
            Path(output_path).write_bytes(base64.b64decode(match.group(1)))
            return True

    # 3. Content as list of parts (OpenRouter / DashScope image parts)
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and "image_url" in part:
                url = part["image_url"].get("url", "")
                if url.startswith("data:image"):
                    b64_data = url.split(",", 1)[1]
                    Path(output_path).write_bytes(base64.b64decode(b64_data))
                    return True
            if isinstance(part, dict) and part.get("type") == "image":
                # Check for OSS URL (DashScope returns remote URLs)
                oss_url = part.get("image", "") or part.get("image_url", {}).get("url", "")
                if oss_url.startswith("http"):
                    import urllib.request
                    try:
                        with urllib.request.urlopen(oss_url, timeout=60) as resp:
                            Path(output_path).write_bytes(resp.read())
                        return True
                    except Exception as e:
                        print(f"Failed to download image from {oss_url}: {e}", file=sys.stderr)
                        continue
                if oss_url.startswith("data:image"):
                    b64_data = oss_url.split(",", 1)[1]
                    Path(output_path).write_bytes(base64.b64decode(b64_data))
                    return True
                # Check for inline base64 data
                data = part.get("data", "")
                if data.startswith("data:image"):
                    b64_data = data.split(",", 1)[1]
                    Path(output_path).write_bytes(base64.b64decode(b64_data))
                    return True

    # 4. DALL-E style: data[].b64_json
    data = result.get("data", [])
    if data and isinstance(data, list):
        b64 = data[0].get("b64_json")
        if b64:
            Path(output_path).write_bytes(base64.b64decode(b64))
            return True

    # 5. DashScope native: output.choices[].message.content[] with image URL
    output = result.get("output", {})
    output_choices = output.get("choices", [])
    if output_choices:
        output_msg = output_choices[0].get("message", {})
        output_content = output_msg.get("content", [])
        if isinstance(output_content, list):
            for part in output_content:
                if isinstance(part, dict) and part.get("type") == "image":
                    img_url = part.get("image", "")
                    if img_url.startswith("http"):
                        import urllib.request
                        try:
                            with urllib.request.urlopen(img_url, timeout=60) as resp:
                                Path(output_path).write_bytes(resp.read())
                            return True
                        except Exception as e:
                            print(f"Failed to download image from {img_url}: {e}", file=sys.stderr)
                            continue
                    if img_url.startswith("data:image"):
                        b64_data = img_url.split(",", 1)[1]
                        Path(output_path).write_bytes(base64.b64decode(b64_data))
                        return True

    print("Could not extract image from API response", file=sys.stderr)
    print(f"Raw response (first 2000 chars): {json.dumps(result, indent=2)[:2000]}", file=sys.stderr)
    return False


def _enhance_gemini(
    image_path: str, prompt: str, config: dict, output_path: str
) -> bool:
    """Enhance via Google Gemini native API."""
    try:
        import google.genai as genai
    except ImportError:
        print("google-genai not installed. Run: pip install google-genai", file=sys.stderr)
        return False

    client = genai.Client(api_key=config["enhance_api_key"])

    try:
        response = client.models.generate_content(
            model=config["enhance_model"],
            contents=[
                prompt,
                genai.types.Part.from_bytes(
                    data=Path(image_path).read_bytes(),
                    mime_type="image/png",
                ),
            ],
            config=genai.types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Extract image from response
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                Path(output_path).write_bytes(part.inline_data.data)
                return True
            if hasattr(part, "text") and part.text:
                # Check for base64 image in text
                import re
                text = part.text
                match = re.search(r"data:image/\w+;base64,([A-Za-z0-9+/=]+)", text)
                if match:
                    Path(output_path).write_bytes(base64.b64decode(match.group(1)))
                    return True

        print("No image found in Gemini response", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Gemini enhancement failed: {e}", file=sys.stderr)
        return False


# ── Main ────────────────────────────────────────────────────────────────────

def enhance(
    image_path: str,
    output_path: str,
    svg_code: str | None,
    mode: str,
    art_style: str,
    config: dict,
) -> bool:
    """Run enhancement. Returns True on success."""

    # Build the enhancement prompt based on mode
    if mode == "none":
        prompt = _build_prompt_none()
    elif mode == "code":
        if not svg_code:
            print("Mode 'code' requires --svg", file=sys.stderr)
            return False
        prompt = _build_prompt_code(svg_code, art_style)
    elif mode == "code2prompt":
        if not svg_code:
            print("Mode 'code2prompt' requires --svg", file=sys.stderr)
            return False
        spec = _code_to_prompt(svg_code, art_style, config)
        if not spec:
            print("code2prompt failed, falling back to 'code' mode", file=sys.stderr)
            prompt = _build_prompt_code(svg_code, art_style)
        else:
            prompt = _build_prompt_code2prompt(spec, art_style)
    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        return False

    # Call the appropriate provider
    provider = config["enhance_provider"]
    if provider == "gemini":
        return _enhance_gemini(image_path, prompt, config, output_path)
    else:
        return _enhance_openai(image_path, prompt, config, output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Enhance scientific figures via image generation API"
    )
    parser.add_argument("image", help="Path to layout PNG")
    parser.add_argument("--svg", help="Path to SVG source code")
    parser.add_argument(
        "--mode",
        choices=["none", "code", "code2prompt"],
        default="code2prompt",
        help="Enhancement mode (default: code2prompt)",
    )
    parser.add_argument("--style", help="Art style description")
    parser.add_argument("-o", "--output", help="Output path (default: <input>_enhanced.png)")
    parser.add_argument("--api-key", help="API key (overrides config)")
    parser.add_argument("--base-url", help="API base URL (overrides config)")
    parser.add_argument("--model", help="Model name (overrides config)")
    args = parser.parse_args()

    config = load_config()

    if args.api_key:
        config["enhance_api_key"] = args.api_key
    if args.base_url:
        config["enhance_base_url"] = args.base_url
    if args.model:
        config["enhance_model"] = args.model

    if not config.get("enhance_api_key"):
        print(
            "No enhancement API key configured. Set AUTOFIGURE_ENHANCE_API_KEY.",
            file=sys.stderr,
        )
        sys.exit(1)

    image_path = args.image
    if not Path(image_path).exists():
        print(f"File not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        p = Path(image_path)
        output_path = str(p.parent / f"{p.stem}_enhanced.png")

    svg_code = None
    if args.svg:
        svg_path = Path(args.svg)
        if svg_path.exists():
            svg_code = svg_path.read_text()

    art_style = args.style or config.get("art_style", "Modern scientific illustration")

    print(f"Enhancing via {config['enhance_provider']}: {config['enhance_model']}")
    print(f"Mode: {args.mode}, Style: {art_style}")

    ok = enhance(image_path, output_path, svg_code, args.mode, art_style, config)
    if ok:
        print(output_path)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()