# Translated from Chinese for Biorouter from Haojae/scipilot-figure-skill scripts/visual_qa.py (MIT, commit 43098ddb9e6a). See LICENSE-UPSTREAM.
"""
scipilot-figure-skill :: visual_qa.py
=====================================
Post-render "programmatic self-check" and "rendered preview": the machine layer of the self-check loop.

Division of labour:
- **The program (this script)** catches **deterministic** problems: missing glyphs, text clipped at the canvas edge, overlapping tick labels.
- **The agent viewing the figure** (the visual review in figure-qa's SKILL.md) catches **perceptual** problems: legends covering data,
  whether panel labels line up, whether colours separate in grayscale, the overall impression.

Only the two layers together make the full loop: plot, render a PNG, programmatic check plus visual review, fix, look again.

Main functions
--------
- ``render_preview(fig_or_path, out_png, dpi)``: render a medium-resolution PNG
  for the agent to view with its image-reading tool (a vector PDF cannot be checked for pixel overlap directly; rasterise it first).
- ``audit_layout(fig)``: returns ``[(severity, msg), ...]``:
  * **Missing glyphs** (FAIL): while rendering, intercept both of matplotlib's warning channels,
    warnings and logging; any "missing from font" report means the figure will show boxes or garbled text.
  * **Clipped text** (WARN): a Text's window_extent extends past the canvas edge.
  * **Overlapping tick labels** (WARN): bounding boxes of adjacent tick labels intersect horizontally or vertically.

Severity follows check_figure.py: INFO < WARN < FAIL.

Usage
-----
    from visual_qa import render_preview, audit_layout, print_report

    fig, ax = plt.subplots()
    ...
    png = render_preview(fig, "figs/_preview.png", dpi=150)  # for the agent to view
    issues = audit_layout(fig)
    print_report(issues)

CLI:
    python visual_qa.py demo                       # run the self-check demo
    python visual_qa.py figs/fig1.png --preview out.png
"""
from __future__ import annotations

import argparse
import io
import logging
import os
import sys
import warnings

import matplotlib.pyplot as plt
import matplotlib.text as mtext


# A Windows GBK terminal raises UnicodeEncodeError when printing Chinese. Use reconfigure rather than replacing
# sys.stdout: idempotent, creates no new object, and never closes the underlying stream when several scripts import it.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SEVERITY = {"INFO": 0, "WARN": 1, "FAIL": 2}
_GLYPH_MARKERS = ("missing from", "Glyph", "findfont")


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


class _GlyphLogHandler(logging.Handler):
    """Capture matplotlib logger records about missing glyphs or fonts."""

    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record):
        msg = record.getMessage()
        if any(m in msg for m in _GLYPH_MARKERS):
            self.messages.append(msg)


def _draw_and_collect_glyph_warnings(fig) -> list[str]:
    """
    Render the figure once and collect missing-glyph warnings from both the warnings and logging channels.

    matplotlib versions report missing glyphs differently: older versions use warnings.warn,
    newer ones use logging. Hooking both misses nothing. Rendering also readies the renderer
    for the window_extent measurements that follow.
    """
    handler = _GlyphLogHandler()
    mpl_logger = logging.getLogger("matplotlib")
    prev_level = mpl_logger.level
    mpl_logger.setLevel(logging.WARNING)
    mpl_logger.addHandler(handler)

    collected: list[str] = []
    try:
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            # drawing in memory is enough, nothing is written; draw also triggers missing-glyph warnings
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100)
            buf.close()
        for w in wlist:
            s = str(w.message)
            if any(m in s for m in _GLYPH_MARKERS):
                collected.append(s)
    finally:
        mpl_logger.removeHandler(handler)
        mpl_logger.setLevel(prev_level)

    collected.extend(handler.messages)
    # deduplicate, keeping order
    seen, uniq = set(), []
    for m in collected:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


def _visible_texts(fig) -> list:
    out = []
    for t in fig.findobj(mtext.Text):
        try:
            if t.get_visible() and t.get_text().strip():
                out.append(t)
        except Exception:
            continue
    return out


def audit_layout(fig, clip_tol_px: float = 2.0, overlap_tol_px: float = 1.0
                 ) -> list[tuple[str, str]]:
    """
    Run the layout self-check on a matplotlib Figure. Returns [(severity, msg), ...].

    Checks:
        1. Missing glyphs (FAIL): no font found for Chinese or special symbols.
        2. Clipped text (WARN): a title, axis label or annotation extends past the canvas.
        3. Overlapping tick labels (WARN): bounding boxes of adjacent x or y tick labels intersect.

    Non-destructive: renders and measures only, never changes the figure.
    """
    issues: list[tuple[str, str]] = []

    # ---- 1. Missing glyphs (also renders once to ready the renderer) ----
    glyph_msgs = _draw_and_collect_glyph_warnings(fig)
    if glyph_msgs:
        sample = " | ".join(glyph_msgs[:3])
        issues.append((
            "FAIL",
            f"Missing glyphs found; the figure will show boxes or garbled text: {sample[:240]}. "
            "For Chinese text, set a CJK font first (rcParams['font.sans-serif'] = ['Noto Sans CJK SC', ...]); "
            "if the boxes are minus signs, set axes.unicode_minus=False."
        ))

    try:
        renderer = fig.canvas.get_renderer()
    except Exception:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

    W = float(fig.bbox.width)
    H = float(fig.bbox.height)

    # ---- 2. Clipped text ----
    # Tick labels past the edge are handled by constrained_layout / bbox_inches='tight', and
    # the tick overlap check covers them, so skip them here and watch only user text (titles, axis labels, annotations),
    # avoiding false alarms from ticks touching the edge under constrained_layout.
    tick_ids = set()
    for ax in fig.axes:
        for tl in (*ax.get_xticklabels(), *ax.get_xticklabels(minor=True),
                   *ax.get_yticklabels(), *ax.get_yticklabels(minor=True)):
            tick_ids.add(id(tl))

    clipped: list[str] = []
    for t in _visible_texts(fig):
        if id(t) in tick_ids:
            continue
        try:
            bb = t.get_window_extent(renderer)
        except Exception:
            continue
        if (bb.x0 < -clip_tol_px or bb.y0 < -clip_tol_px
                or bb.x1 > W + clip_tol_px or bb.y1 > H + clip_tol_px):
            txt = t.get_text().strip().replace("\n", " ")
            if txt:
                clipped.append(txt[:24])
    if clipped:
        uniq = list(dict.fromkeys(clipped))[:6]
        issues.append((
            "WARN",
            f"This text may extend past the canvas and be clipped: {uniq}. "
            "use fig.set_layout_engine('constrained') or save with bbox_inches='tight'; "
            "wrap or shorten long titles and labels."
        ))

    # ---- 3. Overlapping tick labels ----
    overlap_axes = 0
    for ax in fig.axes:
        if ax.get_subplotspec() is None:
            continue
        if _ticklabels_overlap(ax.get_xticklabels(), renderer,
                               axis="x", tol=overlap_tol_px):
            overlap_axes += 1
            continue
        if _ticklabels_overlap(ax.get_yticklabels(), renderer,
                               axis="y", tol=overlap_tol_px):
            overlap_axes += 1
    if overlap_axes:
        issues.append((
            "WARN",
            f"{overlap_axes} panel(s) have overlapping tick labels. "
            "x axis: ax.tick_params(axis='x', rotation=30), or fewer ticks or shorter labels; "
            "y axis: a taller panel or fewer ticks."
        ))

    return issues


def _ticklabels_overlap(labels, renderer, axis: str, tol: float) -> bool:
    """Whether bounding boxes of adjacent tick labels intersect. axis='x' checks horizontally, 'y' vertically."""
    boxes = []
    for l in labels:
        try:
            if l.get_visible() and l.get_text().strip():
                boxes.append(l.get_window_extent(renderer))
        except Exception:
            continue
    if len(boxes) < 2:
        return False
    if axis == "x":
        boxes.sort(key=lambda b: b.x0)
        return any(a.x1 - b.x0 > tol for a, b in zip(boxes, boxes[1:]))
    else:
        boxes.sort(key=lambda b: b.y0)
        return any(a.y1 - b.y0 > tol for a, b in zip(boxes, boxes[1:]))


def render_preview(fig_or_path, out_png: str = "_preview.png",
                   dpi: int = 150) -> str:
    """
    Render a PNG preview for the agent to view.

    Args:
        fig_or_path: a matplotlib Figure (the main path of the self-check loop), or the path of a saved
            image (a raster is returned as is; a PDF needs the optional PyMuPDF).
        out_png: output PNG path.
        dpi: preview resolution, default 150 (enough to see text and overlaps without a huge file).

    Returns:
        the path of a PNG the agent can view (the original path for a raster source).
    """
    if hasattr(fig_or_path, "savefig"):
        _ensure_parent(out_png)
        fig_or_path.savefig(out_png, dpi=dpi, bbox_inches="tight")
        return out_png

    path = str(fig_or_path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in {"png", "tif", "tiff", "jpg", "jpeg", "bmp"}:
        return path
    if ext == "pdf":
        try:
            import fitz  # PyMuPDF, optional
        except ImportError as e:
            raise RuntimeError(
                "Rendering a PDF preview needs PyMuPDF (pip install pymupdf). "
                "For the self-check loop it is better to pass the matplotlib Figure to render_preview directly "
                "and finish the visual review before export."
            ) from e
        doc = fitz.open(path)
        pix = doc[0].get_pixmap(dpi=dpi)
        _ensure_parent(out_png)
        pix.save(out_png)
        doc.close()
        return out_png
    raise RuntimeError(f"Cannot make a preview from .{ext} files; pass a Figure or a raster image.")


def print_report(issues: list[tuple[str, str]]) -> str:
    """Print the audit_layout result and return the verdict (PASS/WARN/FAIL)."""
    if not issues:
        print("  [PASS] the programmatic check found no missing glyphs, clipping or tick overlap.")
        print("  >>> the visual review for perceptual problems is still needed (see figure-qa's SKILL.md).")
        return "PASS"
    max_sev = max(SEVERITY[s] for s, _ in issues)
    verdict = {2: "FAIL", 1: "WARN", 0: "INFO"}[max_sev]
    for sev, msg in sorted(issues, key=lambda x: -SEVERITY[x[0]]):
        print(f"  [{sev}] {msg}")
    print(f"  >>> verdict: {verdict} (after fixing, render the PNG again and review it)")
    return verdict


def _demo() -> int:
    """Build a figure with layout problems to show what audit_layout catches."""
    import numpy as np
    rng = np.random.default_rng(1)

    fig, ax = plt.subplots(figsize=(3.0, 2.2))
    cats = [f"very_long_condition_name_{i}" for i in range(12)]
    ax.bar(range(12), rng.random(12))
    ax.set_xticks(range(12))
    ax.set_xticklabels(cats)  # deliberately not rotated -> the x tick labels overlap
    ax.set_title("An intentionally overlong title that runs off the canvas edge")
    ax.set_ylabel("value")

    print("=== visual_qa demo: self-check of a deliberately broken layout ===")
    issues = audit_layout(fig)
    print_report(issues)
    out = render_preview(fig, "./visual_qa_demo.png", dpi=120)
    print(f"\nPreview written: {out} (view it with the image-reading tool)")
    print("Note: the missing-glyph check FAILs only when, for example, no Chinese font is set; this demo mainly shows clipping and overlap.")
    return 0


def _cli() -> int:
    p = argparse.ArgumentParser(description="scipilot-figure-skill visual QA")
    p.add_argument("target", nargs="?", help="image path, or 'demo'")
    p.add_argument("--preview", metavar="OUT.png",
                   help="render target to a PNG preview at this path")
    p.add_argument("--dpi", type=int, default=150)
    args = p.parse_args()

    if args.target == "demo" or args.target is None:
        return _demo()

    if args.preview:
        out = render_preview(args.target, args.preview, dpi=args.dpi)
        print(f"[visual_qa] preview: {out}")
    else:
        # For a saved file audit_layout needs a Figure object, so only a hint is possible here
        print("[visual_qa] for a saved image only --preview rendering is supported; "
              "call the audit_layout layout check on the Figure object in the plotting script.")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
