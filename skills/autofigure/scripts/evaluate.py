#!/usr/bin/env python3
"""VLM-based visual evaluation of rendered scientific figures.

Sends the rendered PNG (and optionally SVG code + reference figures) to a VLM
for scoring and critique.

Supports:
  - OpenAI-compatible API (OpenRouter, Bianxie, vLLM, etc.)
  - Google Gemini API

Usage:
  python evaluate.py <png_path> [--svg <svg_path>] [--topic paper] \
      [--references <ref_dir>] [--json]
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = SCRIPT_DIR.parent / "references" / "prompts"


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_config() -> dict:
    return {
        "eval_api_key": _env("AUTOFIGURE_EVAL_API_KEY"),
        "eval_base_url": _env("AUTOFIGURE_EVAL_BASE_URL", "https://openrouter.ai/api/v1"),
        "eval_model": _env("AUTOFIGURE_EVAL_MODEL", "google/gemini-2.5-flash"),
        "eval_provider": _env("AUTOFIGURE_EVAL_PROVIDER", "openai"),
    }


def load_eval_prompt() -> str:
    path = PROMPTS_DIR / "evaluate.md"
    if path.exists():
        return path.read_text()
    # Fallback — should not happen if the skill is installed correctly
    return "Evaluate this scientific figure. Be strict. Output JSON with scores."


def encode_image(path: str) -> str:
    """Read an image file and return a base64 data URL."""
    p = Path(path)
    suffix = p.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mime = mime_map.get(suffix, "image/png")
    data = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{data}"


def evaluate_openai(
    png_path: str,
    svg_code: str | None,
    reference_paths: list[str],
    topic: str,
    config: dict,
) -> dict:
    """Evaluate using an OpenAI-compatible vision API."""
    import urllib.request
    import urllib.error

    # Build message content
    content = [{"type": "text", "text": EVAL_PROMPT}]

    # Attach PNG
    content.append({
        "type": "image_url",
        "image_url": {"url": encode_image(png_path), "detail": "high"},
    })

    # Attach reference figures
    for i, ref_path in enumerate(reference_paths):
        content.append({"type": "text", "text": f"Reference figure example {i+1}:"})
        content.append({
            "type": "image_url",
            "image_url": {"url": encode_image(ref_path), "detail": "high"},
        })

    # Attach SVG code as text for structural context
    if svg_code:
        content.append({
            "type": "text",
            "text": f"The raw SVG code for reference:\n```svg\n{svg_code}\n```",
        })

    body = {
        "model": config["eval_model"],
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": 2048,
    }

    url = f"{config['eval_base_url']}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['eval_api_key']}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return _parse_response(result["choices"][0]["message"]["content"])
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")[:500]
        return _fallback(f"HTTP {e.code}: {error_body}")
    except Exception as e:
        return _fallback(str(e))


def evaluate_gemini(png_path: str, svg_code: str | None, config: dict) -> dict:
    """Evaluate using Google Gemini API."""
    try:
        import google.genai as genai
    except ImportError:
        return _fallback("google-genai not installed. Run: pip install google-genai")

    client = genai.Client(api_key=config["eval_api_key"])
    parts = [EVAL_PROMPT]

    # Attach PNG
    parts.append(genai.types.Part.from_bytes(
        data=Path(png_path).read_bytes(),
        mime_type="image/png",
    ))

    if svg_code:
        parts.append(f"The raw SVG code for reference:\n```svg\n{svg_code}\n```")

    try:
        response = client.models.generate_content(
            model=config["eval_model"],
            contents=parts,
        )
        return _parse_response(response.text)
    except Exception as e:
        return _fallback(str(e))


def _parse_response(text: str) -> dict:
    """Parse the VLM JSON response, handling markdown fences."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        import re
        match = re.search(r'\{[\s\S]*"overall_quality"[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return _fallback(f"JSON parse error. Raw response: {text[:300]}")


def _fallback(reason: str) -> dict:
    """Return a neutral fallback evaluation."""
    return {
        "scores": {
            "aesthetic_design": 5.0,
            "content_fidelity": 5.0,
            "layout_readability": 5.0,
        },
        "overall_quality": 5.0,
        "critique_summary": f"Evaluation unavailable: {reason}",
        "specific_issues": ["Evaluation failed — see error above"],
        "improvement_suggestions": ["Re-run evaluation or fix the API configuration"],
        "_error": reason,
    }


def main():
    parser = argparse.ArgumentParser(
        description="VLM-based visual evaluation of figures"
    )
    parser.add_argument("png", help="Path to rendered PNG")
    parser.add_argument("--svg", help="Path to SVG source code (for context)")
    parser.add_argument("--topic", default="paper", help="Figure topic")
    parser.add_argument(
        "--references", help="Directory containing reference PNG files"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument(
        "--api-key", help="API key (overrides config/env)"
    )
    parser.add_argument(
        "--base-url", help="API base URL (overrides config/env)"
    )
    parser.add_argument(
        "--model", help="Model name (overrides config/env)"
    )
    args = parser.parse_args()

    config = load_config()

    # CLI overrides
    if args.api_key:
        config["eval_api_key"] = args.api_key
    if args.base_url:
        config["eval_base_url"] = args.base_url
    if args.model:
        config["eval_model"] = args.model

    if not config.get("eval_api_key"):
        if not args.json:
            print("No VLM API key configured. Set AUTOFIGURE_EVAL_API_KEY.")
        print(json.dumps(_fallback("No API key configured")))
        sys.exit(1)

    # Read SVG code if provided
    svg_code = None
    if args.svg:
        svg_path = Path(args.svg)
        if svg_path.exists():
            svg_code = svg_path.read_text()

    # Collect reference figures
    reference_paths = []
    if args.references:
        ref_dir = Path(args.references)
        if ref_dir.is_dir():
            reference_paths = sorted(
                str(p) for p in ref_dir.glob("*.png")
            )

    if not args.json:
        print(f"Evaluating via {config['eval_provider']}: {config['eval_model']}")

    if config["eval_provider"] == "gemini":
        result = evaluate_gemini(args.png, svg_code, config)
    else:
        result = evaluate_openai(
            args.png, svg_code, reference_paths, args.topic, config
        )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()