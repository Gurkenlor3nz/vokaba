# vokaba/ocr_runner.py
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# NEU:
import builtins
import io


def _needs_paddlex_dot_version_hack() -> bool:
    """
    Detects the common packaging mistake: paddlex package exists but paddlex/.version is missing.
    (Dotfiles often get dropped by cp .../*)
    """
    try:
        for p in list(sys.path):
            pp = Path(p)
            pkg_dir = pp / "paddlex"
            if pkg_dir.exists() and pkg_dir.is_dir():
                if not (pkg_dir / ".version").exists():
                    return True
        return False
    except Exception:
        return False


def _patch_open_for_missing_paddlex_version():
    """
    Very narrow workaround: if PaddleX tries to read paddlex/.version and it's missing,
    return a dummy version string instead of crashing.
    """
    real_open = builtins.open

    def patched_open(file, *args, **kwargs):
        try:
            p = os.fspath(file)
            p_norm = p.replace("\\", "/")
            if p_norm.endswith("/paddlex/.version"):
                mode = "r"
                if args and isinstance(args[0], str):
                    mode = args[0]
                if "b" in mode:
                    return io.BytesIO(b"0.0.0")
                return io.StringIO("0.0.0")
        except Exception:
            pass
        return real_open(file, *args, **kwargs)

    return real_open, patched_open


def main() -> int:
    ap = argparse.ArgumentParser(description="Vokaba OCR subprocess runner (PaddleOCR)")
    ap.add_argument("--image", required=True, help="Path to image (jpg/png)")
    ap.add_argument("--lang", default="en", help="PaddleOCR lang, e.g. en, german, fr ...")
    ap.add_argument("--textline-ori", action="store_true", help="Use textline orientation")
    ap.add_argument("--cache-dir", required=True, help="Model cache dir")
    ap.add_argument("--out", required=True, help="Output JSON file path")
    ap.add_argument("--no-source-check", action="store_true", help="Disable model source connectivity check")
    args = ap.parse_args()

    img_path = Path(args.image).expanduser().resolve()
    if not img_path.exists():
        print(f"File not found: {img_path}", file=sys.stderr)
        return 2

    cache_dir = Path(args.cache_dir).expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("DISABLE_AUTO_LOGGING_CONFIG", "1")
    os.environ.setdefault("PADDLEX_HOME", str(cache_dir))
    os.environ.setdefault("PADDLEX_CACHE_DIR", str(cache_dir))
    if args.no_source_check:
        os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("OMP_NUM_THREADS", "1")

    # NEU: targeted workaround for missing paddlex/.version
    use_hack = _needs_paddlex_dot_version_hack()
    real_open = None

    try:
        if use_hack:
            real_open, patched_open = _patch_open_for_missing_paddlex_version()
            builtins.open = patched_open
            print(
                "WARN: paddlex/.version missing (packaging dotfile). "
                "Using safe fallback. Fix your build to include dotfiles.",
                file=sys.stderr,
            )

        from paddleocr import PaddleOCR

        ocr = PaddleOCR(lang=args.lang, use_textline_orientation=args.textline_ori)
        results = ocr.predict(str(img_path), use_textline_orientation=args.textline_ori)

        json_pages = []
        for res in results or []:
            j = getattr(res, "json", None)
            if isinstance(j, dict):
                json_pages.append(j)

        out_path.write_text(json.dumps(json_pages, ensure_ascii=False), encoding="utf-8")
        return 0

    except Exception as e:
        print(f"OCR subprocess failed: {e}", file=sys.stderr)
        return 1

    finally:
        if use_hack and real_open is not None:
            builtins.open = real_open


if __name__ == "__main__":
    raise SystemExit(main())
