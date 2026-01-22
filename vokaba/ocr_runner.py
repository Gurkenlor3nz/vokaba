# vokaba/ocr_runner.py
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

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

    # Keep Paddle/PaddleX quiet and avoid extra checks
    os.environ.setdefault("DISABLE_AUTO_LOGGING_CONFIG", "1")
    os.environ.setdefault("PADDLEX_HOME", str(cache_dir))
    os.environ.setdefault("PADDLEX_CACHE_DIR", str(cache_dir))
    if args.no_source_check:
        os.environ["DISABLE_MODEL_SOURCE_CHECK"] = "True"

    # CPU-stability knobs (helpful on some systems)
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("OMP_NUM_THREADS", "1")

    try:
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

if __name__ == "__main__":
    raise SystemExit(main())
