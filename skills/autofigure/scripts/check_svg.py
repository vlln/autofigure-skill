#!/usr/bin/env python3
"""SVG structural checker — catches only absolute errors, not style preferences.

Usage:
  python check_svg.py <svg_path> [--json] [--canvas W H]

Exit code 0 = no errors found. Non-zero = errors found.
Outputs JSON to stdout (with --json) or a human-readable summary.
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

SVG_NS = "http://www.w3.org/2000/svg"


def parse_svg(path: str) -> Tuple[ET.Element | None, List[str]]:
    """Parse SVG file. Returns (root, errors)."""
    errors = []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        return None, [f"XML parse error: {e}"]
    except FileNotFoundError:
        return None, [f"File not found: {path}"]

    if root.tag != f"{{{SVG_NS}}}svg":
        errors.append(
            f"Root element is <{root.tag.split('}')[-1]}>, expected <svg>"
        )

    return root, errors


def check_duplicate_ids(root: ET.Element) -> List[str]:
    """Check for duplicate id attributes (SVG spec violation)."""
    errors = []
    seen_ids: Dict[str, str] = {}  # id -> first element tag

    for el in root.iter():
        el_id = el.get("id")
        if el_id:
            tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if el_id in seen_ids:
                errors.append(
                    f"Duplicate id '{el_id}': found on <{seen_ids[el_id]}> "
                    f"and <{tag}>"
                )
            else:
                seen_ids[el_id] = tag

    return errors


def get_text_bbox(el: ET.Element) -> Tuple[float, float, float, float] | None:
    """Estimate bounding box for a text element.

    SVG text elements don't have width/height attributes, so we estimate
    from font-size and character count. This is approximate (0.6em per
    char width, 1.2em height) but sufficient for overlap detection.
    """
    x = el.get("x")
    y = el.get("y")
    if x is None or y is None:
        return None
    try:
        x, y = float(x), float(y)
    except ValueError:
        return None

    text = "".join(el.itertext()).strip()
    if not text:
        return None

    # Get font-size (default 16px)
    style = el.get("style", "")
    font_size = 16  # default
    for part in ("font-size:", "font-size :"):
        if part in style:
            idx = style.index(part) + len(part)
            rest = style[idx:].strip()
            size_str = ""
            for ch in rest:
                if ch in "0123456789.":
                    size_str += ch
                else:
                    break
            if size_str:
                font_size = float(size_str)
                break
    # Also check standalone font-size attribute
    fs_attr = el.get("font-size")
    if fs_attr:
        try:
            font_size = float(fs_attr.replace("px", "").strip())
        except ValueError:
            pass

    char_count = len(text)
    est_w = char_count * font_size * 0.55
    est_h = font_size * 1.25

    return (x, y, est_w, est_h)


def get_bbox(el: ET.Element) -> Tuple[float, float, float, float] | None:
    """Get bounding box from element attributes. Returns (x, y, w, h) or None."""
    x = el.get("x")
    y = el.get("y")
    w = el.get("width")
    h = el.get("height")

    # Also check cx/cy/r for circles
    if x is None and (cx := el.get("cx")):
        r = float(el.get("r", 0))
        x = float(cx) - r
        w = 2 * r
    if y is None and (cy := el.get("cy")):
        r = float(el.get("r", 0))
        y = float(cy) - r
        h = 2 * r

    if x is None or y is None:
        return None
    try:
        return (float(x), float(y), float(w or 0), float(h or 0))
    except ValueError:
        return None


def _rects_overlap(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, by: float, bw: float, bh: float,
) -> Tuple[bool, float, float]:
    """Check overlap between two rects. Returns (overlaps, overlap_area, min_area)."""
    ox = max(ax, bx)
    oy = max(ay, by)
    ow = min(ax + aw, bx + bw) - ox
    oh = min(ay + ah, by + bh) - oy
    if ow <= 0 or oh <= 0:
        return False, 0.0, 0.0
    overlap = ow * oh
    min_area = min(aw * ah, bw * bh)
    return overlap > 0, overlap, min_area


def check_bounds(root: ET.Element, canvas_w: int, canvas_h: int) -> List[str]:
    """Check for elements entirely outside the canvas."""
    errors = []
    rendered_tags = {
        "rect", "circle", "ellipse", "image", "text",
        "path", "line", "polyline", "polygon",
    }
    for el in root.iter():
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag not in rendered_tags:
            continue
        parent = find_parent(root, el)
        if parent is not None and parent.tag == f"{{{SVG_NS}}}defs":
            continue
        bbox = get_bbox(el)
        if bbox is None:
            continue
        x, y, w, h = bbox

        if w <= 0 or h <= 0:
            if w < 0 or h < 0:
                errors.append(
                    f"<{tag}> has negative dimensions: "
                    f"width={w}, height={h}"
                )
            continue

        # Fully outside canvas
        if x + w < 0 or y + h < 0 or x > canvas_w or y > canvas_h:
            el_id = el.get("id", "")
            id_str = f" id='{el_id}'" if el_id else ""
            errors.append(
                f"<{tag}{id_str}> at ({x},{y}) size ({w}x{h}) "
                f"is entirely outside canvas ({canvas_w}x{canvas_h})"
            )

    return errors


def check_placeholders(root: ET.Element) -> List[str]:
    """Check that gray placeholder rects have [icon]: descriptions nearby."""
    errors = []
    placeholder_rects = []

    for el in root.iter():
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag != "rect":
            continue
        style = el.get("style", "")
        fill = el.get("fill", "")
        # Detect placeholder rects by their gray fill
        is_gray = (
            "fill:#cccccc" in style
            or "fill:#CCCCCC" in style
            or fill.lower() in ("#cccccc", "#ccc", "gray", "grey", "#808080")
        )
        if is_gray:
            placeholder_rects.append(el)

    if not placeholder_rects:
        return []  # No placeholders at all is fine for non-paper topics

    # Check each placeholder has an interior description
    for rect in placeholder_rects:
        bbox = get_bbox(rect)
        if bbox is None:
            continue
        rx, ry, rw, rh = bbox

        # Find text elements whose center falls inside this rect
        has_icon_desc = False
        for text_el in root.iter():
            text_tag = text_el.tag.split("}")[-1] if "}" in text_el.tag else text_el.tag
            if text_tag != "text":
                continue
            text_bbox = get_bbox(text_el)
            if text_bbox is None:
                continue
            tx, ty, tw, th = text_bbox
            text_cx, text_cy = tx + tw / 2, ty + th / 2

            if rx <= text_cx <= rx + rw and ry <= text_cy <= ry + rh:
                text_content = "".join(text_el.itertext()).strip()
                if "[icon]:" in text_content.lower() or "[icon]：" in text_content:
                    has_icon_desc = True
                    break

        if not has_icon_desc:
            rect_id = rect.get("id", "")
            id_str = f" id='{rect_id}'" if rect_id else ""
            errors.append(
                f"Placeholder rect{id_str} at ({rx},{ry}) missing "
                f"[icon]: description inside the box"
            )

    return errors


def check_empty_text(root: ET.Element) -> List[str]:
    """Check for empty text elements (invisible text)."""
    errors = []
    for el in root.iter():
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag != "text":
            continue
        text = "".join(el.itertext()).strip()
        if not text:
            el_id = el.get("id", "")
            id_str = f" id='{el_id}'" if el_id else ""
            errors.append(f"<text{id_str}> has no content")
    return errors


def check_overlapping_siblings(
    root: ET.Element, canvas_w: int, canvas_h: int
) -> List[str]:
    """Check for sibling elements that substantially overlap.

    This is a WARNING-level check: some overlap is intentional (Venn diagrams,
    layered designs). Only flag clear cases: >50% area overlap with no
    connector line between them.

    Filters out noisy intentional overlaps:
      - Large background rects (>60% canvas width or height) overlapping
        smaller inner elements (e.g. section containers with child boxes).
      - Small inner rects fully contained within a larger rect (child-on-parent
        layering, like header bars on section backgrounds).
    """
    warnings = []
    elements = []
    large_threshold_w = canvas_w * 0.6
    large_threshold_h = canvas_h * 0.6

    for el in root.iter():
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        # Only check shape elements (not text, groups, defs)
        if tag not in ("rect", "circle", "ellipse", "path", "polygon", "polyline"):
            continue
        # Skip children of defs (not rendered)
        parent = find_parent(root, el)
        if parent is not None and parent.tag == f"{{{SVG_NS}}}defs":
            continue
        bbox = get_bbox(el)
        if bbox is None:
            continue
        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            continue
        # Skip placeholders (they're meant to overlap with their text)
        style = el.get("style", "")
        fill = el.get("fill", "")
        if (
            "fill:#cccccc" in style
            or fill.lower() in ("#cccccc", "#ccc", "gray", "grey")
        ):
            continue
        elements.append((el, x, y, w, h))

    # Check pairs
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            el_a, ax, ay, aw, ah = elements[i]
            el_b, bx, by, bw, bh = elements[j]

            # Check if they share the same parent (siblings)
            pa = find_parent(root, el_a)
            pb = find_parent(root, el_b)
            if pa is not pb:
                continue

            # Compute overlap area
            ox = max(ax, bx)
            oy = max(ay, by)
            ow = min(ax + aw, bx + bw) - ox
            oh = min(ay + ah, by + bh) - oy

            if ow <= 0 or oh <= 0:
                continue

            overlap_area = ow * oh
            min_area = min(aw * ah, bw * bh)

            # Only flag if overlap > 50% of the smaller element
            if overlap_area > 0.5 * min_area:
                # Skip: large background rects overlapping inner elements
                # (section containers with child boxes — intentional layering)
                a_is_large = aw > large_threshold_w or ah > large_threshold_h
                b_is_large = bw > large_threshold_w or bh > large_threshold_h
                if a_is_large or b_is_large:
                    continue

                # Skip: smaller element fully contained within larger
                # (header bars, inner panels on section backgrounds)
                a_in_b = (
                    ax >= bx and ay >= by
                    and ax + aw <= bx + bw and ay + ah <= by + bh
                )
                b_in_a = (
                    bx >= ax and by >= ay
                    and bx + bw <= ax + aw and by + bh <= ay + ah
                )
                if a_in_b or b_in_a:
                    continue

                a_id = el_a.get("id", "")
                b_id = el_b.get("id", "")
                a_tag = el_a.tag.split("}")[-1]
                b_tag = el_b.tag.split("}")[-1]
                warnings.append(
                    f"WARNING: <{a_tag} id='{a_id}'> and <{b_tag} id='{b_id}'> "
                    f"have substantial overlap ({overlap_area / min_area:.0%} "
                    f"of smaller element). Verify this is intentional."
                )

    return warnings


def _get_panel_group(root: ET.Element, el: ET.Element) -> ET.Element | None:
    """Get the top-level <g> panel group that contains el, if any.

    Panel groups are direct <g> children of the root <svg>.
    Returns None if el is not inside a panel group (e.g. top-level elements).
    """
    for child in root:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag != "g":
            continue
        for descendant in child.iter():
            if descendant is el:
                return child
    return None


def check_cross_group_overlap(
    root: ET.Element, canvas_w: int, canvas_h: int
) -> List[str]:
    """Check for shape elements that substantially overlap across different panels.

    Panel groups are direct <g> children of <svg>. Elements in different panels
    should not visually overlap. This catches bugs where content from Panel A
    bleeds into Panel B.

    Filters:
      - Skips placeholder rects (intentionally overlap with content)
      - Skips large background rects (panel containers) overlapping inner content
      - Only checks shape elements (rect, circle, ellipse, path, polygon)
      - Threshold: >20% overlap of the smaller element
    """
    errors = []
    shape_tags = {"rect", "circle", "ellipse", "path", "polygon"}
    large_threshold_w = canvas_w * 0.5
    large_threshold_h = canvas_h * 0.5
    overlap_threshold = 0.40  # 40% of smaller element

    elements = []  # (el, x, y, w, h, panel_group)
    for el in root.iter():
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        if tag not in shape_tags:
            continue
        # Skip children of defs
        parent = find_parent(root, el)
        if parent is not None and parent.tag == f"{{{SVG_NS}}}defs":
            continue
        bbox = get_bbox(el)
        if bbox is None:
            continue
        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            continue
        # Skip placeholders
        style = el.get("style", "")
        fill = el.get("fill", "")
        if "fill:#cccccc" in style or fill.lower() in (
            "#cccccc", "#ccc", "gray", "grey"
        ):
            continue
        panel = _get_panel_group(root, el)
        elements.append((el, x, y, w, h, panel))

    # Check cross-panel pairs
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            el_a, ax, ay, aw, ah, panel_a = elements[i]
            el_b, bx, by, bw, bh, panel_b = elements[j]

            # Must be in different panels
            if panel_a is panel_b:
                continue
            # Skip if either has no panel (top-level element)
            if panel_a is None or panel_b is None:
                continue

            overlaps, overlap_area, min_area = _rects_overlap(
                ax, ay, aw, ah, bx, by, bw, bh
            )
            if not overlaps:
                continue
            if overlap_area <= overlap_threshold * min_area:
                continue

            # Skip: smaller element fully contained within larger
            # (container-content layering across panels — e.g. a card border
            # and its inner content drawn as separate rects)
            a_in_b = (
                ax >= bx and ay >= by
                and ax + aw <= bx + bw and ay + ah <= by + bh
            )
            b_in_a = (
                bx >= ax and by >= ay
                and bx + bw <= ax + aw and by + bh <= ay + ah
            )
            if a_in_b or b_in_a:
                continue

            # Skip: one element is a large background container
            a_is_bg = aw > large_threshold_w or ah > large_threshold_h
            b_is_bg = bw > large_threshold_w or bh > large_threshold_h
            if a_is_bg or b_is_bg:
                continue

            a_id = el_a.get("id", "")
            b_id = el_b.get("id", "")
            errors.append(
                f"Cross-panel overlap: <{el_a.tag.split('}')[-1]}{a_id}> "
                f"overlaps <{el_b.tag.split('}')[-1]}{b_id}> "
                f"({overlap_area / min_area:.0%} of smaller). "
                f"Different panels should not overlap."
            )

    return errors


def check_text_shape_cross_overlap(
    root: ET.Element, canvas_w: int, canvas_h: int
) -> List[str]:
    """Check for text elements that bleed outside their own panel.

    A text element whose center falls outside its parent panel group's
    bounding box is likely bleeding into another panel — a layout bug.
    """
    errors = []
    overlap_threshold = 0.15  # 15% of the text bbox area
    large_threshold_w = canvas_w * 0.5
    large_threshold_h = canvas_h * 0.5

    # Step 1: Compute bounding box for each panel group
    panel_bboxes: dict = {}  # panel_group -> (x, y, w, h)
    shape_tags = {"rect", "circle", "ellipse", "path", "polygon"}

    for child in root:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag != "g":
            continue
        # Find bounding box of all shape children in this panel
        px_min, py_min = float("inf"), float("inf")
        px_max, py_max = 0.0, 0.0
        found = False
        for el in child.iter():
            etag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if etag not in shape_tags:
                continue
            bbox = get_bbox(el)
            if bbox is None:
                continue
            x, y, w, h = bbox
            if w <= 0 or h <= 0:
                continue
            px_min = min(px_min, x)
            py_min = min(py_min, y)
            px_max = max(px_max, x + w)
            py_max = max(py_max, y + h)
            found = True
        if found:
            panel_bboxes[child] = (
                px_min, py_min, px_max - px_min, py_max - py_min
            )

    # Step 2: Check each text element
    for text_el in root.iter():
        tag = text_el.tag.split("}")[-1] if "}" in text_el.tag else text_el.tag
        if tag != "text":
            continue
        text_bbox = get_text_bbox(text_el)
        if text_bbox is None:
            continue
        tx, ty, tw, th = text_bbox
        text_area = tw * th
        if text_area <= 0:
            continue
        text_content = "".join(text_el.itertext()).strip()
        if not text_content:
            continue

        text_panel = _get_panel_group(root, text_el)
        if text_panel is None:
            continue  # top-level text, skip

        # Check if text center is inside its own panel's bbox
        text_cx, text_cy = tx + tw / 2, ty + th / 2
        if text_panel in panel_bboxes:
            pbx, pby, pbw, pbh = panel_bboxes[text_panel]
            if pbx <= text_cx <= pbx + pbw and pby <= text_cy <= pby + pbh:
                continue  # text is inside its own panel — OK

        # Text center is outside its own panel — check if it overlaps
        # any shape in a different panel
        for el in root.iter():
            stag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if stag not in shape_tags:
                continue
            parent = find_parent(root, el)
            if parent is not None and parent.tag == f"{{{SVG_NS}}}defs":
                continue
            sbbox = get_bbox(el)
            if sbbox is None:
                continue
            sx, sy, sw, sh = sbbox
            if sw <= 0 or sh <= 0:
                continue
            shape_panel = _get_panel_group(root, el)
            if shape_panel is text_panel or shape_panel is None:
                continue

            overlaps, overlap_area, _ = _rects_overlap(
                tx, ty, tw, th, sx, sy, sw, sh
            )
            if not overlaps:
                continue
            if overlap_area <= overlap_threshold * text_area:
                continue

            s_id = el.get("id", "")
            errors.append(
                f"Text outside its panel: '{text_content[:40]}...' "
                f"center=({text_cx:.0f},{text_cy:.0f}) "
                f"overlaps <{stag}{s_id}> in another panel "
                f"({overlap_area / text_area:.0%} of text bbox)."
            )
            break  # one error per text element is enough

    return errors


def find_parent(root: ET.Element, target: ET.Element) -> ET.Element | None:
    """Find the parent of target in the tree rooted at root."""
    for parent in root.iter():
        for child in parent:
            if child is target:
                return parent
    return None


def check_empty_svg(root: ET.Element) -> List[str]:
    """Check if the SVG has essentially no visible content."""
    visible_tags = {
        f"{{{SVG_NS}}}rect",
        f"{{{SVG_NS}}}circle",
        f"{{{SVG_NS}}}ellipse",
        f"{{{SVG_NS}}}path",
        f"{{{SVG_NS}}}line",
        f"{{{SVG_NS}}}polyline",
        f"{{{SVG_NS}}}polygon",
        f"{{{SVG_NS}}}text",
        f"{{{SVG_NS}}}image",
    }
    has_content = any(el.tag in visible_tags for el in root.iter())
    if not has_content:
        return ["SVG has no visible elements (rect, circle, text, path, etc.)"]
    return []


def run_checks(
    svg_path: str, canvas_w: int = 1333, canvas_h: int = 750
) -> dict:
    """Run all checks. Returns a dict with errors, warnings, and summary."""
    result = {
        "file": svg_path,
        "canvas": {"width": canvas_w, "height": canvas_h},
        "errors": [],
        "warnings": [],
        "passed": True,
    }

    root, parse_errors = parse_svg(svg_path)
    if root is None:
        result["errors"] = parse_errors
        result["passed"] = False
        return result

    # Absolute errors
    result["errors"].extend(check_duplicate_ids(root))
    result["errors"].extend(check_bounds(root, canvas_w, canvas_h))
    result["errors"].extend(check_empty_text(root))
    result["errors"].extend(check_empty_svg(root))

    # Placeholder check (warning in non-paper, error in paper — but we
    # always report it as an error since the prompt requires [icon]:)
    placeholder_issues = check_placeholders(root)
    result["errors"].extend(placeholder_issues)

    # Cross-panel overlap checks (structural errors: content from different
    # panels should not visually overlap)
    result["errors"].extend(
        check_cross_group_overlap(root, canvas_w, canvas_h)
    )
    result["errors"].extend(
        check_text_shape_cross_overlap(root, canvas_w, canvas_h)
    )

    # Warnings (not absolute errors, but worth flagging)
    result["warnings"].extend(
        check_overlapping_siblings(root, canvas_w, canvas_h)
    )

    result["passed"] = len(result["errors"]) == 0

    # Only include warnings if they exist
    if not result["warnings"]:
        del result["warnings"]

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Check SVG for absolute errors"
    )
    parser.add_argument("svg_path", help="Path to SVG file")
    parser.add_argument(
        "--json", action="store_true", help="Output JSON to stdout"
    )
    parser.add_argument(
        "--canvas-w", type=int, default=1333, help="Canvas width"
    )
    parser.add_argument(
        "--canvas-h", type=int, default=750, help="Canvas height"
    )
    args = parser.parse_args()

    result = run_checks(args.svg_path, args.canvas_w, args.canvas_h)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["passed"]:
            print(f"PASS: {args.svg_path}")
            if "warnings" in result:
                for w in result["warnings"]:
                    print(f"  {w}")
        else:
            print(f"FAIL: {args.svg_path} ({len(result['errors'])} errors)")
            for e in result["errors"]:
                print(f"  ERROR: {e}")
            if "warnings" in result:
                for w in result["warnings"]:
                    print(f"  {w}")

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
