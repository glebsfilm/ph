#!/usr/bin/env python3
"""
HTML generator for glebsfilm — editorial monograph build.

Reads each photo's dimensions during build so <img> tags get correct
width/height attributes (prevents Cumulative Layout Shift, fixes the
"cream box around lazy images" bug).

Per-photo camera/film metadata can be set via PHOTO_META below. Any
photo not listed gets the collection's default. Edit and re-run.

NOTE on Cloudflare Analytics:
  Replace CF_BEACON_TOKEN with the token from your Cloudflare dashboard.
"""

from pathlib import Path
from PIL import Image
import json
import hashlib

# Root of the site = wherever this script lives. Works on GitHub
# Actions runners, in Docker, on Windows — anywhere.
DST = Path(__file__).resolve().parent

# Cache-busting: an 8-char content hash appended to the CSS/JS URLs.
# Changes automatically whenever the file's contents change, which
# forces browsers and Cloudflare to fetch the fresh copy. When the
# file is unchanged, the hash stays the same so caching still works.
def asset_version(rel_path: str) -> str:
    p = DST / rel_path
    if not p.exists():
        return "0"
    return hashlib.md5(p.read_bytes()).hexdigest()[:8]

CSS_VER = asset_version("styles/site.css")
JS_VER  = asset_version("js/site.js")

CF_BEACON_TOKEN = "REPLACE_WITH_YOUR_CF_BEACON_TOKEN"
SITE_URL        = "https://www.glebsfilm.com"

# ============================================================ #
# Collection definitions                                       #
# ============================================================ #

COLLECTIONS = [
    # (slug, title, prefix, folder, blurb, default_camera, default_film)
    # Photo count is auto-detected from the images/ folder at build time —
    # add new photos with `add_photo.py` and they show up automatically.
    ("automotive", "Automotive", "a", "automotive",
     "Engines, leather, light on chrome.",
     "Camera",  "Film stock"),
    ("landscape",  "Landscape",  "l", "landscapes",
     "Wide air, slow water, the patience of stone.",
     "Camera",  "Film stock"),
    ("cityscape",  "Cityscape",  "c", "cityscapes",
     "Steel, glass, and the lives that pass between them.",
     "Camera",  "Film stock"),
]

# Per-photo overrides for camera/film metadata.
# Key is "{slug}-{photo_index}", e.g. "landscapes-3".
# Format: (camera, film_stock). Any photo not listed inherits the
# collection default above.
# Photo metadata — camera + film stock per photo — lives in
# photo_meta.json so it can be edited via the GitHub web UI without
# touching Python. Both per-collection defaults and per-photo
# overrides are supported.
def _load_meta():
    p = DST / "photo_meta.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"⚠  photo_meta.json is not valid JSON: {e}")
        return {}

_META = _load_meta()


# ============================================================ #
# Build helpers                                                #
# ============================================================ #

# Cache image dimensions so we only read each file once.
_dim_cache = {}
def img_dims(path: Path):
    if path in _dim_cache:
        return _dim_cache[path]
    with Image.open(path) as im:
        _dim_cache[path] = im.size
    return _dim_cache[path]


def count_photos(folder: str, prefix: str) -> int:
    """How many photos does this collection have? Scan the filesystem."""
    images_dir = DST / "images" / folder
    if not images_dir.exists():
        return 0
    nums = []
    for p in images_dir.glob(f"{prefix}*-1600.jpg"):
        stem = p.stem.rsplit("-", 1)[0]
        num_str = stem[len(prefix):]
        try:
            nums.append(int(num_str))
        except ValueError:
            continue
    # Return the highest sequential number (handles gaps if photos were deleted)
    return max(nums) if nums else 0


def photo_indices(folder: str, prefix: str) -> list:
    """Sorted list of photo numbers that actually exist on disk."""
    images_dir = DST / "images" / folder
    if not images_dir.exists():
        return []
    nums = []
    for p in images_dir.glob(f"{prefix}*-1600.jpg"):
        stem = p.stem.rsplit("-", 1)[0]
        num_str = stem[len(prefix):]
        try:
            nums.append(int(num_str))
        except ValueError:
            continue
    return sorted(nums)


def meta_for(slug: str, i: int, fallback_cam: str, fallback_film: str):
    """Return (camera, film) for this photo, looking up:
       1. photo_meta.json -> photos -> {slug}-{i}
       2. photo_meta.json -> _defaults -> {slug}
       3. The fallback values passed in (from COLLECTIONS)
    """
    photos = _META.get("photos", {}) or {}
    key = f"{slug}-{i}"
    if key in photos and isinstance(photos[key], dict):
        e = photos[key]
        return (e.get("camera", fallback_cam),
                e.get("film",   fallback_film))
    defaults = (_META.get("_defaults") or {}).get(slug, {})
    return (defaults.get("camera", fallback_cam),
            defaults.get("film",   fallback_film))


def head(*, title, description, canonical, depth=0, extra_head=""):
    root = "../" if depth else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="keywords" content="Photography, Film photography, 35mm film, 120mm film, analog art, vintage photography">
  <meta name="author" content="glebsfilm">
  <link rel="canonical" href="{canonical}">

  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
  <link rel="manifest" href="/site.webmanifest">
  <link rel="mask-icon" href="/safari-pinned-tab.svg" color="#1a1814">
  <meta name="msapplication-TileColor" content="#F5F1EA">
  <meta name="theme-color" content="#F5F1EA">

  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:image" content="{SITE_URL}/assets/logo_square-640.webp">
  <meta property="og:image:width" content="640">
  <meta property="og:image:height" content="640">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image" content="{SITE_URL}/assets/logo_square-640.webp">

  <script defer src="https://static.cloudflareinsights.com/beacon.min.js"
          data-cf-beacon='{{"token": "{CF_BEACON_TOKEN}"}}'></script>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT@0,9..144,300..600,30..100;1,9..144,300..600,30..100&family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..600&family=IBM+Plex+Mono:wght@300;400;500&display=swap">

  <link rel="stylesheet" href="{root}styles/site.css?v={CSS_VER}">
  {extra_head}
</head>"""


def navbar(*, depth=0, index_label, nav_items, current=None):
    root = "../" if depth else ""
    li_html = "\n".join(
        f'      <li><a href="{href}"{" aria-current=\"page\"" if (current and current==label) else ""}>{label}</a></li>'
        for label, href in nav_items
    )
    return f"""<header class="site-nav">
  <div class="site-nav__index">{index_label}</div>
  <a class="site-nav__brand" href="{root}index.html">glebsfilm</a>
  <button class="site-nav__toggle" aria-label="Menu" aria-expanded="false">
    <svg width="22" height="14" viewBox="0 0 22 14" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="0" y1="2" x2="22" y2="2"/><line x1="0" y1="12" x2="22" y2="12"/></svg>
  </button>
  <ul class="site-nav__links">
{li_html}
  </ul>
</header>"""


def footer(*, depth=0):
    root = "../" if depth else ""
    return f"""<footer class="site-foot">
  <div class="container">
    <div class="site-foot__grid">
      <div>
        <p class="site-foot__brand">glebsfilm</p>
        <p class="site-foot__tag">A film photography portfolio. 35mm &amp; 120 film, SLR and TLR cameras.</p>
      </div>
      <div class="site-foot__col">
        <h4>Visit</h4>
        <ul>
          <li><a href="{root}index.html">Index</a></li>
          <li><a href="{root}about.html">About</a></li>
          <li><a href="https://glebsfilm.darkroom.com" target="_blank" rel="noopener">Prints</a></li>
        </ul>
      </div>
      <div class="site-foot__col">
        <h4>Elsewhere</h4>
        <ul>
          <li><a href="https://www.instagram.com/glebsfilm" target="_blank" rel="noopener">Instagram</a></li>
          <li><a href="https://www.tiktok.com/@glebsfilm_" target="_blank" rel="noopener">TikTok</a></li>
          <li><a href="https://www.lomography.com/homes/glebsfilm/" target="_blank" rel="noopener">Lomography</a></li>
          <li><a href="mailto:glebsfilm@gmail.com">Email</a></li>
        </ul>
      </div>
    </div>
    <div class="site-foot__base">
      <p class="site-foot__copyright">© 2024 glebsfilm — All photographs by the author</p>
      <p class="site-foot__set">Set in Fraunces &amp; IBM Plex Mono</p>
    </div>
  </div>
</footer>"""


def picture_with_dims(stem_path, *, sizes_attr, jpg_full_path):
    """stem_path is the URL stem; jpg_full_path is the absolute path
    on disk so we can read intrinsic dimensions."""
    w, h = img_dims(jpg_full_path)
    return (
        f'<picture>'
        f'<source type="image/webp" '
        f'srcset="{stem_path}-960.webp 960w, {stem_path}-1600.webp 1600w" '
        f'sizes="{sizes_attr}">'
        f'<img src="{stem_path}-1600.jpg" alt="" loading="lazy" decoding="async" '
        f'width="{w}" height="{h}">'
        f'</picture>'
    )


def scripts(*, depth=0):
    root = "../" if depth else ""
    return f'<script src="{root}js/site.js?v={JS_VER}" defer></script>'


# ============================================================ #
# Pages                                                         #
# ============================================================ #

def build_index():
    NAV = [("Index", "#collections"), ("About", "about.html"),
           ("Prints", "https://glebsfilm.darkroom.com")]
    total = sum(count_photos(c[3], c[2]) for c in COLLECTIONS)

    cards_html = ""
    for i, c in enumerate(COLLECTIONS, 1):
        slug, title, prefix, folder, *_ = c
        count = count_photos(folder, prefix)
        prio = ' fetchpriority="high"' if i == 1 else ''
        # Use the first photo from each collection as the card image.
        jpg_path = DST / "images" / folder / f"{prefix}1-1600.jpg"
        w, h = img_dims(jpg_path)
        cards_html += f'''      <a href="collections/{slug}.html" class="collection-card">
        <div class="collection-card__media">
          <span class="mono collection-card__num">No. {i:02d}</span>
          <span class="mono collection-card__view">View →</span>
          <picture>
            <source type="image/webp" srcset="images/{folder}/{prefix}1-960.webp">
            <img src="images/{folder}/{prefix}1-1600.jpg" alt="" decoding="async" width="{w}" height="{h}"{prio}>
          </picture>
        </div>
        <div class="collection-card__meta">
          <h3 class="collection-card__title">{title}</h3>
          <span class="mono collection-card__count">{count} frames</span>
        </div>
      </a>
'''

    page = f"""{head(
        title="glebsfilm — Analogue Photography",
        description="A film photography portfolio. Landscapes, cityscapes, and automotive work on 35mm and 120 film, by glebsfilm.",
        canonical=f"{SITE_URL}/",
        depth=0,
        extra_head='<link rel="preload" as="image" href="assets/background-1920.webp" fetchpriority="high">',
    )}
<body>
  {navbar(depth=0, index_label="Index — Analogue Photography",
          nav_items=NAV, current="Index")}

  <main>
    <section class="hero" id="top">
      <div class="hero__image" aria-hidden="true"></div>

      <div class="hero__corner">
        <p class="mono">Est. on Film</p>
        <p class="mono"><span class="hero__corner__sep"></span>35mm · 120</p>
      </div>

      <div class="hero__content">
        <div class="hero__title-wrap">
          <h1 class="hero__title">
            <span class="word">Analogue</span>
            <span class="word">photographs,</span>
            <span class="word"><em>by hand.</em></span>
          </h1>
        </div>
        <div class="hero__meta">
          <span class="mono">A portfolio by</span>
          <span class="mono hero__meta__name">glebsfilm</span>
          <span class="mono hero__meta__sub">{total} frames · {len(COLLECTIONS)} series</span>
        </div>
      </div>

      <a class="hero__scroll" href="#collections" aria-label="Scroll to collections">
        <span class="mono">Scroll</span>
        <span class="hero__scroll__line"></span>
      </a>
    </section>

    <section class="collections" id="collections">
      <div class="container">
        <header class="collections__header">
          <div>
            <p class="eyebrow collections__eyebrow">— I. The Work</p>
            <h2 class="collections__title">Three series, gathered.</h2>
          </div>
          <div class="collections__count">
            <p class="mono">{len(COLLECTIONS):02d} collections</p>
            <p class="mono collections__count__sub">{total} total frames</p>
          </div>
        </header>

        <div class="collections__grid">
{cards_html}        </div>
      </div>
    </section>
  </main>

  {footer(depth=0)}
  {scripts(depth=0)}
</body>
</html>"""
    (DST / "index.html").write_text(page, encoding="utf-8")
    print("wrote index.html")


def build_about():
    NAV = [("Index", "index.html"), ("About", "about.html"),
           ("Prints", "https://glebsfilm.darkroom.com")]
    total = sum(count_photos(c[3], c[2]) for c in COLLECTIONS)
    portrait = DST / "assets" / "logo_square-640.webp"
    # The about-portrait source is a webp; Pillow can read it.
    w, h = img_dims(portrait)

    page = f"""{head(
        title="About — glebsfilm",
        description="About glebsfilm — a film photographer working with 35mm and 120 film on SLR and TLR cameras.",
        canonical=f"{SITE_URL}/about.html",
        depth=0,
    )}
<body>
  {navbar(depth=0, index_label="About — Colophon",
          nav_items=NAV, current="About")}

  <main class="about">
    <div class="container">
      <div class="about__grid">
        <div class="about__portrait">
          <picture>
            <img src="assets/logo_square-640.webp" alt="" decoding="async" width="{w}" height="{h}">
          </picture>
          <p class="mono about__portrait__caption">Self-portrait · 35mm</p>
        </div>

        <div class="about__copy">
          <p class="eyebrow about__eyebrow">— II. About the photographer</p>
          <h1 class="about__title">Hello.<br><em>Thanks for stopping by.</em></h1>

          <p class="about__lede">I got hooked on film photography after finding my parents' old camera and developing a forgotten roll inside.</p>

          <div class="about__body">
            <p>I shoot 135 and 120 film on SLR and TLR cameras &mdash; the slow, deliberate kind of picture-taking that asks you to look first and shoot second. Every frame is metered, focused and composed by hand; every roll developed and scanned with care.</p>
            <p>Feel free to drop me a line on <a href="https://www.instagram.com/glebsfilm/" target="_blank" rel="noopener">Instagram</a> or <a href="https://www.lomography.com/homes/glebsfilm/" target="_blank" rel="noopener">Lomography</a>, or send an email to <a href="mailto:glebsfilm@gmail.com">glebsfilm@gmail.com</a> &mdash; questions, prints, collaborations, all welcome.</p>
          </div>

          <dl class="about__contact">
            <dt>Cameras</dt><dd>SLR · TLR</dd>
            <dt>Formats</dt><dd>35mm · 120</dd>
            <dt>Output</dt><dd>{total} frames · {len(COLLECTIONS)} series</dd>
            <dt>Prints</dt><dd><a href="https://glebsfilm.darkroom.com" target="_blank" rel="noopener">glebsfilm.darkroom.com</a></dd>
          </dl>
        </div>
      </div>
    </div>
  </main>

  {footer(depth=0)}
  {scripts(depth=0)}
</body>
</html>"""
    (DST / "about.html").write_text(page, encoding="utf-8")
    print("wrote about.html")


def build_collection(idx, c):
    slug, title, prefix, folder, blurb, def_cam, def_film = c
    NAV = [("Index", "../index.html"), ("About", "../about.html"),
           ("Prints", "https://glebsfilm.darkroom.com")]

    indices = photo_indices(folder, prefix)
    count = len(indices)
    if count == 0:
        print(f"⚠  skipping {slug}: no photos found in images/{folder}/")
        return

    prev_idx = (idx - 2) % len(COLLECTIONS)
    next_idx = idx % len(COLLECTIONS)
    prev_c = COLLECTIONS[prev_idx]
    next_c = COLLECTIONS[next_idx]

    # Build a flat list of frames — CSS columns handles the masonry.
    frames = []
    for i in indices:
        stem_url  = f"../images/{folder}/{prefix}{i}"
        jpg_path  = DST / "images" / folder / f"{prefix}{i}-1600.jpg"
        cam, film = meta_for(slug, i, def_cam, def_film)
        w, h = img_dims(jpg_path)
        frames.append(f'''        <figure class="frame">
          <div class="frame__picture">
            <picture>
              <source type="image/webp" srcset="{stem_url}-960.webp 960w, {stem_url}-1600.webp 1600w" sizes="(min-width: 720px) 50vw, 100vw">
              <img src="{stem_url}-1600.jpg" alt="" loading="lazy" decoding="async" width="{w}" height="{h}">
            </picture>
          </div>
          <figcaption class="frame__caption">
            <span class="mono frame__index">{i:03d} / {count:03d}</span>
            <span class="mono frame__meta">{cam} &middot; {film}</span>
          </figcaption>
        </figure>''')
    gallery_html = "\n".join(frames)

    roman = ["I", "II", "III"][idx-1]

    page = f"""{head(
        title=f"{title} — glebsfilm",
        description=f"{title}: {blurb} Film photography on 35mm and 120 film by glebsfilm.",
        canonical=f"{SITE_URL}/collections/{slug}.html",
        depth=1,
    )}
<body>
  {navbar(depth=1, index_label=f"{roman} · {title}", nav_items=NAV)}

  <main>
    <section class="coll-head">
      <div class="container">
        <div class="coll-head__grid">
          <div>
            <p class="eyebrow coll-head__eyebrow">— Series {roman} of {len(COLLECTIONS):02d}</p>
            <h1 class="coll-head__title">{title}.</h1>
          </div>
          <div class="coll-head__meta">
            <p class="mono">{count:03d} frames</p>
            <p class="mono coll-head__meta__sub">35mm · 120</p>
          </div>
        </div>
      </div>
    </section>

    <section>
      <div class="container">
        <div class="gallery">
{gallery_html}
        </div>
      </div>
    </section>

    <nav class="coll-foot">
      <div class="container">
        <div class="coll-foot__inner">
          <div class="coll-foot__prev">
            <span class="mono coll-foot__label">← Previous</span>
            <a class="coll-foot__link" href="{prev_c[0]}.html">{prev_c[1]}</a>
          </div>
          <a class="coll-foot__home" href="../index.html">Return to Index</a>
          <div class="coll-foot__next">
            <span class="mono coll-foot__label">Next →</span>
            <a class="coll-foot__link" href="{next_c[0]}.html">{next_c[1]}</a>
          </div>
        </div>
      </div>
    </nav>
  </main>

  {footer(depth=1)}
  {scripts(depth=1)}
</body>
</html>"""
    (DST / "collections" / f"{slug}.html").write_text(page, encoding="utf-8")
    print(f"wrote collections/{slug}.html  ({count} images)")


def build_robots_and_sitemap():
    (DST / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\nSitemap: https://www.glebsfilm.com/sitemap.xml\n",
        encoding="utf-8",
    )
    pages = [("/", "1.00"), ("/about.html", "0.80")]
    pages += [(f"/collections/{c[0]}.html", "0.80") for c in COLLECTIONS]
    urls = "\n".join(
        f"  <url><loc>{SITE_URL}{p}</loc><priority>{pr}</priority></url>"
        for p, pr in pages
    )
    (DST / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
        encoding="utf-8",
    )
    print("wrote robots.txt + sitemap.xml")


def build_webmanifest_and_browserconfig():
    (DST / "site.webmanifest").write_text(
        '{\n  "name": "glebsfilm",\n  "short_name": "glebsfilm",\n'
        '  "description": "Analogue film photography portfolio by glebsfilm",\n'
        '  "icons": [\n'
        '    { "src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png" },\n'
        '    { "src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png" }\n'
        '  ],\n'
        '  "theme_color": "#F5F1EA",\n'
        '  "background_color": "#F5F1EA",\n'
        '  "display": "standalone",\n'
        '  "start_url": "/"\n}\n',
        encoding="utf-8",
    )
    (DST / "browserconfig.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<browserconfig>\n  <msapplication>\n'
        '    <tile>\n      <square150x150logo src="/mstile-150x150.png"/>\n'
        '      <TileColor>#F5F1EA</TileColor>\n    </tile>\n  </msapplication>\n</browserconfig>\n',
        encoding="utf-8",
    )
    print("wrote site.webmanifest + browserconfig.xml")


if __name__ == "__main__":
    build_index()
    build_about()
    for i, c in enumerate(COLLECTIONS, 1):
        build_collection(i, c)
    build_robots_and_sitemap()
    build_webmanifest_and_browserconfig()
    print("\nAll pages generated.")
