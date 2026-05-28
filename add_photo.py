#!/usr/bin/env python3
"""
Add a new photo to a collection.

USAGE
  python3 add_photo.py <collection> <source_image_path>

EXAMPLES
  python3 add_photo.py landscape  ~/Pictures/scans/2024-09-mamiya.jpg
  python3 add_photo.py automotive ~/Downloads/0345.jpg
  python3 add_photo.py cityscape  ./tokyo_07.jpg

Collections (slugs):
  automotive   landscape   cityscape

WHAT THIS DOES
  1. Figures out the next sequential number for that collection by
     scanning the images folder (e.g. if l1..l16 exist, the new one
     becomes l17).
  2. Resizes the source to 960px (mobile) and 1600px (desktop) on
     the long edge.
  3. Writes:
         images/<folder>/<stem>-960.webp     (mobile, WebP)
         images/<folder>/<stem>-1600.webp    (desktop, WebP)
         images/<folder>/<stem>-1600.jpg     (JPEG fallback)
  4. Tells you to run build_html.py to regenerate the HTML.

The original source file is NOT copied into the project — keep your
high-res masters wherever you normally store them.

If you want the new photo to be the homepage cover for its
collection, swap it into position 1 yourself (rename l17-*.* to
l1-*.* and the existing l1-*.* to l17-*.*).
"""

import argparse
import sys
from pathlib import Path
from PIL import Image, ImageOps

# (slug, prefix, folder) — must match build_html.py's COLLECTIONS
COLLECTIONS = {
    "automotive": ("a", "automotive"),
    "landscape":  ("l", "landscapes"),
    "cityscape":  ("c", "cityscapes"),
}

ROOT = Path(__file__).resolve().parent
WEBP_QUALITY = 82
JPEG_QUALITY = 84
SIZES = [960, 1600]   # long-edge widths to generate


def find_next_n(images_dir: Path, prefix: str) -> int:
    """Highest existing photo index for this prefix + 1."""
    if not images_dir.exists():
        return 1
    nums = []
    # Look for *-1600.jpg derivatives — one per source photo.
    for p in images_dir.glob(f"{prefix}*-1600.jpg"):
        stem = p.stem.rsplit("-", 1)[0]   # "l16-1600" -> "l16"
        num_str = stem[len(prefix):]       # "l16" -> "16"
        try:
            nums.append(int(num_str))
        except ValueError:
            continue
    return max(nums) + 1 if nums else 1


def resize_long_edge(img: Image.Image, target: int) -> Image.Image:
    w, h = img.size
    if max(w, h) <= target:
        return img.copy()
    if w >= h:
        return img.resize((target, round(h * target / w)), Image.LANCZOS)
    return img.resize((round(w * target / h), target), Image.LANCZOS)


def process(src: Path, out_dir: Path, stem: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        # Honour EXIF orientation, then drop EXIF for privacy & size.
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "P"):
            im = im.convert("RGB")
        for size in SIZES:
            resized = resize_long_edge(im, size)
            (out_dir / f"{stem}-{size}.webp")
            resized.save(out_dir / f"{stem}-{size}.webp",
                         "WEBP", quality=WEBP_QUALITY, method=6)
            if size == max(SIZES):
                resized.save(out_dir / f"{stem}-{size}.jpg",
                             "JPEG", quality=JPEG_QUALITY,
                             optimize=True, progressive=True)


def main():
    ap = argparse.ArgumentParser(
        description="Add a new photo to a collection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    ap.add_argument("collection", choices=list(COLLECTIONS.keys()))
    ap.add_argument("path", type=Path)
    args = ap.parse_args()

    if not args.path.exists():
        sys.exit(f"❌ File not found: {args.path}")
    if args.path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
        sys.exit(f"❌ Not a supported image: {args.path.suffix}")

    prefix, folder = COLLECTIONS[args.collection]
    images_dir = ROOT / "images" / folder
    n = find_next_n(images_dir, prefix)
    stem = f"{prefix}{n}"

    print(f"→ Adding to '{args.collection}' as photo #{n}")
    print(f"  source: {args.path}")
    process(args.path, images_dir, stem)

    print(f"\n✓ Generated:")
    for size in SIZES:
        print(f"    images/{folder}/{stem}-{size}.webp")
    print(f"    images/{folder}/{stem}-1600.jpg")
    print(f"\nNext step: run  `python3 build_html.py`  to regenerate the pages.")


if __name__ == "__main__":
    main()
