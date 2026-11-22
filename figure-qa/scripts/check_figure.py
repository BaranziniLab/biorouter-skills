# Translated from Chinese for Biorouter from Haojae/scipilot-figure-skill scripts/check_figure.py (MIT, commit 43098ddb9e6a). See LICENSE-UPSTREAM.
"""
scipilot-figure-skill :: check_figure.py
========================================
Pre-submission figure compliance audit.

Checks each file: format (vector, raster, or disallowed JPEG), pixel size and DPI,
and the embedded font type of vector PDFs (must be TrueType/Type 42), and prints the issues.
Non-destructive: read-only, never modifies the figure.

Usage
-----
    from check_figure import check_figure, print_report
    issues, info = check_figure("figs/fig1.pdf", min_dpi=300, target_inches=(3.5, 2.625))
    print_report("figs/fig1.pdf", issues, info)

CLI:
    python check_figure.py figs/fig1.pdf figs/fig2.png --min-dpi 300
    python check_figure.py figs/*.pdf --strict   # any FAIL exits 2
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Any

JPEG_FORMATS = {"jpg", "jpeg"}
VECTOR_FORMATS = {"pdf", "svg", "eps"}
RASTER_OK_FORMATS = {"png", "tiff", "tif"}

# A higher severity number is more severe
SEVERITY = {"INFO": 0, "WARN": 1, "FAIL": 2}


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower().lstrip(".")


def _check_raster(path: str, ext: str, min_dpi: int,
                  target_inches: tuple[float, float] | None) -> tuple[list, dict]:
    """Compliance checks for raster images (PNG/TIFF/JPEG)."""
    issues: list[tuple[str, str]] = []
    info: dict[str, Any] = {"category": "raster", "ext": ext}

    if ext in JPEG_FORMATS:
        issues.append(("FAIL",
                       "JPEG is unsuitable for line or text data plots (lossy compression). "
                       "Use PDF/SVG (vector) or PNG/TIFF (raster) instead."))

    try:
        from PIL import Image
    except ImportError:
        issues.append(("INFO",
                       "Pillow is not installed, skipping the pixel and DPI checks: "
                       "install Pillow to enable them."))
        return issues, info

    try:
        img = Image.open(path)
        info["size_px"] = img.size  # (w, h)
        dpi = img.info.get("dpi")
        info["dpi"] = dpi
    except Exception as e:
        issues.append(("FAIL", f"Cannot read image: {e}"))
        return issues, info

    if dpi is None:
        issues.append(("WARN",
                       "The file has no embedded DPI metadata. Journals often derive the final size from DPI; "
                       "set it explicitly with fig.savefig(dpi=300)."))
    else:
        dx = dpi[0] if isinstance(dpi, tuple) else dpi
        # PIL roundtrips DPI as float and may give 299.9994 for a value saved
        # at 300; round before compare to absorb that.
        dx_rounded = round(float(dx))
        if dx_rounded < min_dpi:
            issues.append(("FAIL",
                           f"DPI = {dx_rounded} is below the required {min_dpi}. "
                           "Save again with savefig(dpi=...)."))
        if target_inches is not None:
            tw, th = target_inches
            actual_w_in = info["size_px"][0] / float(dx)
            actual_h_in = info["size_px"][1] / float(dx)
            tol = 0.1  # tolerance in inches
            if abs(actual_w_in - tw) > tol or abs(actual_h_in - th) > tol:
                issues.append((
                    "WARN",
                    f"Actual size ≈ {actual_w_in:.2f}×{actual_h_in:.2f} in, "
                    f"target {tw}×{th} in. Set figsize=({tw}, {th}) "
                    "when plotting; do not rescale again in Word or LaTeX."
                ))
    return issues, info


def _check_pdf_fonts(path: str) -> list[tuple[str, str]]:
    """Check the embedded font types of a PDF: many journals reject Type 3 (CFF outlines)."""
    issues: list[tuple[str, str]] = []
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # noqa: F401
        except ImportError:
            issues.append(("INFO",
                           "pypdf / PyPDF2 is not installed, skipping the embedded font type check. "
                           "Install pypdf to enable it."))
            return issues

    try:
        reader = PdfReader(path)
    except Exception as e:
        issues.append(("WARN", f"Cannot parse the PDF to check its fonts: {e}"))
        return issues

    bad_fonts: list[str] = []
    not_embedded: list[str] = []
    for page in reader.pages:
        try:
            resources = page.get("/Resources")
            if not resources:
                continue
            fonts = resources.get("/Font")
            if not fonts:
                continue
            for fname, fobj in fonts.items():
                font = fobj.get_object()
                subtype = str(font.get("/Subtype", ""))
                base = str(font.get("/BaseFont", "?"))
                descriptor = font.get("/FontDescriptor")
                if descriptor is None and "/DescendantFonts" in font:
                    # Type0 (composite) fonts, which matplotlib writes for pdf.fonttype 42,
                    # keep their descriptor on the descendant CIDFont.
                    descendants = font["/DescendantFonts"]
                    descendants = descendants.get_object() if hasattr(descendants, "get_object") else descendants
                    if descendants:
                        descriptor = descendants[0].get_object().get("/FontDescriptor")
                if descriptor:
                    descriptor = descriptor.get_object()
                    embedded = any(k in descriptor for k in
                                   ("/FontFile", "/FontFile2", "/FontFile3"))
                else:
                    embedded = False
                if "Type3" in subtype:
                    bad_fonts.append(f"{base} ({subtype})")
                elif not embedded and "Type1" not in subtype:
                    not_embedded.append(base)
        except Exception:
            continue
    if bad_fonts:
        issues.append((
            "FAIL",
            f"The PDF contains Type 3 fonts: {', '.join(set(bad_fonts))[:200]}. "
            "Type 3 fonts blur when enlarged and many journals reject them. "
            "Set rcParams['pdf.fonttype'] = 42 in matplotlib and save again."
        ))
    if not_embedded:
        issues.append((
            "WARN",
            f"These fonts may not be embedded in the PDF: {', '.join(set(not_embedded))[:200]}. "
            "Other computers will show substitute fonts."
        ))
    return issues


def _check_svg(path: str) -> list[tuple[str, str]]:
    """Quick SVG check: warn about base64-embedded raster images (they defeat vector output)."""
    issues: list[tuple[str, str]] = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            head = f.read(50000)
    except Exception as e:
        issues.append(("WARN", f"Cannot read SVG: {e}"))
        return issues
    if "data:image/png;base64" in head or "data:image/jpeg;base64" in head:
        issues.append(("WARN",
                       "The SVG contains a base64-embedded raster image, which loses the benefit of vector output. "
                       "Check whether imshow or an image overlay was used by mistake."))
    return issues


def check_figure(path: str, min_dpi: int = 300,
                 target_inches: tuple[float, float] | None = None
                 ) -> tuple[list[tuple[str, str]], dict]:
    """
    Audit one figure. Returns (issues, info).
    issues: [(severity, message), ...]; severity ∈ {INFO, WARN, FAIL}
    info: metadata dictionary (format, pixels, DPI and so on)
    """
    issues: list[tuple[str, str]] = []
    info: dict[str, Any] = {"path": path}

    if not os.path.exists(path):
        return [("FAIL", f"File not found: {path}")], info

    ext = _ext(path)
    info["ext"] = ext
    info["size_bytes"] = os.path.getsize(path)

    if ext in VECTOR_FORMATS:
        info["category"] = "vector"
        if ext == "pdf":
            issues.extend(_check_pdf_fonts(path))
        elif ext == "svg":
            issues.extend(_check_svg(path))
    elif ext in RASTER_OK_FORMATS or ext in JPEG_FORMATS:
        sub_issues, sub_info = _check_raster(path, ext, min_dpi, target_inches)
        issues.extend(sub_issues)
        info.update(sub_info)
    else:
        issues.append(("WARN", f"Unrecognised extension: .{ext}"))

    return issues, info


def print_report(path: str, issues: list, info: dict) -> str:
    """Print one figure's audit in readable form; returns the overall verdict string."""
    print(f"\n--- {path} ---")
    if "category" in info:
        print(f"  category: {info['category']}  ext: {info['ext']}  "
              f"size: {info.get('size_bytes', '?')} B")
    if info.get("size_px"):
        print(f"  pixels: {info['size_px'][0]}x{info['size_px'][1]}  "
              f"dpi: {info.get('dpi')}")

    if not issues:
        print("  [PASS] no issues.")
        return "PASS"

    max_sev = max(SEVERITY[s] for s, _ in issues)
    verdict = {2: "FAIL", 1: "WARN", 0: "INFO"}[max_sev]
    for severity, msg in sorted(issues, key=lambda x: -SEVERITY[x[0]]):
        print(f"  [{severity}] {msg}")
    print(f"  >>> verdict: {verdict}")
    return verdict


def _cli() -> int:
    p = argparse.ArgumentParser(description="scipilot-figure-skill compliance checker")
    p.add_argument("paths", nargs="+", help="figure file paths; globs allowed")
    p.add_argument("--min-dpi", type=int, default=300)
    p.add_argument("--width-in", type=float, help="target width (inches)")
    p.add_argument("--height-in", type=float, help="target height (inches)")
    p.add_argument("--strict", action="store_true",
                   help="any FAIL gives exit code 2")
    args = p.parse_args()

    target = None
    if args.width_in and args.height_in:
        target = (args.width_in, args.height_in)

    expanded: list[str] = []
    for pat in args.paths:
        m = glob.glob(pat)
        expanded.extend(m if m else [pat])

    any_fail = False
    for path in expanded:
        issues, info = check_figure(path, min_dpi=args.min_dpi, target_inches=target)
        verdict = print_report(path, issues, info)
        if verdict == "FAIL":
            any_fail = True

    print()
    if args.strict and any_fail:
        print("[scipilot-figure-skill] strict mode: at least one FAIL — exit 2")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
