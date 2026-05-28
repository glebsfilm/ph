#!/usr/bin/env python3
"""
process_images.py — find un-processed source images and generate the
WebP/JPEG variants the site needs.

A "source image" is a file inside images/<folder>/ named like
<prefix>N.<ext> (e.g. l17.jpg, a3.jpg, c12.png). For each such file
that doesn't yet have a matching <prefix>N-1600.jpg derivative, this
script writes:

    <stem>-960.webp     (mobile)
    <stem>-1600.webp    (desktop)
    <stem>-1600.jpg     (JPEG fallback)

Safe to run repeatedly — already-processed images are skipped.

Used by the GitHub Action so you can just drop a JPG into the right
folder on github.com and let CI process it. You can also run it
locally:

    python3 process_images.py
"""

import re
from pathlib import Path
from PIL import Image, ImageOps

# (prefix, folder) — must match build_html.py's COLLECTIONS
COLLECTIONS = [
    ("a", "automotive"),
    ("l", "landscapes"),
    ("c", "cityscapes"),
]

ROOT = Path(__file__).resolve().parent
WEBP_QUALITY = 82
JPEG_QUALITY = 84
SIZES = [960, 1600]
SOURCE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def is_source(path: Path, prefix: str) -> bool:
    """True iff this is a source like 'l17.jpg' (prefix + digits only)."""
    if path.suffix.lower() not in SOURCE_EXTS:
        return False
    return bool(re.fullmatch(f"{prefix}\\d+", path.stem))


def resize_long_edge(img: Image.Image, target: int) -> Image.Image:
    w, h = img.size
    if max(w, h) <= target:
        return img.copy()
    if w >= h:
        return img.resize((target, round(h * target / w)), Image.LANCZOS)
    return img.resize((round(w * target / h), target), Image.LANCZOS)


def process(src: Path, out_dir: Path, stem: str):
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "P"):
            im = im.convert("RGB")
        for size in SIZES:
            resized = resize_long_edge(im, size)
            resized.save(out_dir / f"{stem}-{size}.webp",
                         "WEBP", quality=WEBP_QUALITY, method=6)
            if size == max(SIZES):
                resized.save(out_dir / f"{stem}-{size}.jpg",
                             "JPEG", quality=JPEG_QUALITY,
                             optimize=True, progressive=True)


def main():
    done, skipped = 0, 0
    for prefix, folder in COLLECTIONS:
        d = ROOT / "images" / folder
        if not d.exists():
            continue
        for src in sorted(d.iterdir()):
            if not is_source(src, prefix):
                continue
            if (d / f"{src.stem}-1600.jpg").exists():
                skipped += 1
                continue
            print(f"  processing  images/{folder}/{src.name}")
            process(src, d, src.stem)
            done += 1
    if done:
        print(f"\n✓ Processed {done} new image(s). ({skipped} already-processed skipped.)")
    else:
        print(f"Nothing new to process. ({skipped} already-processed images checked.)")


if __name__ == "__main__":
    main()
