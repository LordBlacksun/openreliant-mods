"""Writes the mods' site into site/: the index page, which browses the mods by category, with each
mod's thumbnail, name, version, author, what it needs, its description and the download of its
latest release; a page for each mod, mods/<mod>/, with its pictures, what it is, its download, its
total downloads and its releases; updates/, every mod's releases, newest first; and mods.json, the
released mods as data, which OpenReliant's GET MODS screen reads to list and install them from the
game.

    python3 .github/scripts/site.py
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys

from mods import ROOT, REPOSITORY, Category, Mod, all_categories, git, problems, tree, version_tuple

SITE = ROOT / "site"
# The site's address. mods.json uses absolute links, since the game reads it from anywhere.
SITE_URL = "https://openreliant.github.io/openreliant-mods/"
# The format number of mods.json. Raise it when a key changes meaning. Adding a key doesn't need
# it: OpenReliant ignores keys it doesn't know.
INDEX_FORMAT = 1

STYLE = """
/* Newtown, by Roger White, from Roger's Fonts: the face OpenReliant draws the game's menus in, from
   the OpenReliant website on the same host. */
@font-face { font-family: "Newtown"; src: url("/openreliant/fonts/Newtown.ttf") format("truetype"); font-display: swap; }
:root {
  --bg: #07080c; --card: #10131b; --card-edge: #232938; --text: #e8eaf0; --muted: #9aa3b5;
  --accent: #f08a2c; --accent-dim: #8a4a14; --red: #c8352a;
  --display: "Rajdhani", system-ui, sans-serif;
  --title: "Newtown", "Rajdhani", system-ui, sans-serif;
  /* The display's corner brackets, as round the wing's icons: four short orange corners. */
  --brackets:
    linear-gradient(var(--accent), var(--accent)) top left / 18px 2px,
    linear-gradient(var(--accent), var(--accent)) top left / 2px 18px,
    linear-gradient(var(--accent), var(--accent)) top right / 18px 2px,
    linear-gradient(var(--accent), var(--accent)) top right / 2px 18px,
    linear-gradient(var(--accent), var(--accent)) bottom left / 18px 2px,
    linear-gradient(var(--accent), var(--accent)) bottom left / 2px 18px,
    linear-gradient(var(--accent), var(--accent)) bottom right / 18px 2px,
    linear-gradient(var(--accent), var(--accent)) bottom right / 2px 18px;
  /* A panel with its corners cut, as the game's windows have. */
  --cut: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html { background: var(--bg); }
body {
  margin: 0; color: var(--text); font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif;
  background:
    radial-gradient(1px 1px at 12% 18%, #fff8 50%, transparent 51%),
    radial-gradient(1px 1px at 72% 9%, #fff6 50%, transparent 51%),
    radial-gradient(1px 1px at 38% 62%, #fff5 50%, transparent 51%),
    radial-gradient(1px 1px at 88% 44%, #fff7 50%, transparent 51%),
    radial-gradient(1px 1px at 55% 88%, #fff4 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 25% 80%, #fff6 50%, transparent 51%),
    radial-gradient(ellipse at 80% -10%, #3a1d0c 0%, transparent 55%),
    radial-gradient(ellipse at -10% 110%, #101a3a 0%, transparent 50%),
    var(--bg);
  background-attachment: fixed; min-height: 100vh;
}
main { max-width: 1000px; margin: 0 auto; padding: 0 16px 64px; }
nav.top { display: flex; justify-content: space-between; align-items: center; padding: 20px 0 36px; font-family: var(--display); font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; }
nav.top .brand { color: var(--text); text-decoration: none; font-family: var(--title); font-weight: normal; font-size: 19px; letter-spacing: 0.03em; }
nav.top .brand span, nav.top .links a.current { color: var(--accent); }
nav.top .links a { color: var(--muted); text-decoration: none; margin-left: 22px; font-size: 15px; }
nav.top .links a:hover { color: var(--accent); }
@media (max-width: 520px) { nav.top .links a:not(.keep) { display: none; } nav.top .links a { margin-left: 16px; } }
header { margin-bottom: 36px; }
h1 { font-family: var(--title); margin: 2px 0 10px; font-size: clamp(34px, 7vw, 54px); line-height: 1; letter-spacing: 0.02em; text-transform: uppercase; font-weight: normal; }
header p { margin: 0; max-width: 640px; color: var(--muted); font-size: 17px; }
a { color: var(--accent); text-underline-offset: 2px; }
.mod {
  display: grid; grid-template-columns: 340px 1fr; gap: 24px; padding: 22px; margin-bottom: 22px;
  background: var(--brackets), linear-gradient(180deg, #141824, var(--card));
  background-repeat: no-repeat; box-shadow: inset 0 0 0 1px var(--card-edge);
}
.shot { position: relative; }
.shot img { display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: cover; background: #000; clip-path: var(--cut); }
.mod h2 { font-family: var(--title); margin: 0 0 8px; font-size: 28px; line-height: 1.1; letter-spacing: 0.03em; text-transform: uppercase; font-weight: normal; }
.where { margin: 0 0 4px; font-family: var(--display); font-weight: 600; font-size: 14px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
.where a { color: var(--muted); text-decoration: none; }
.where a:hover { color: var(--accent); }
.badges { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.badge { font-family: var(--display); font-weight: 600; font-size: 14px; letter-spacing: 0.06em; text-transform: uppercase; padding: 2px 10px; border: 1px solid var(--card-edge); color: var(--muted); background: #0b0e15; }
.badge.version { color: var(--accent); border-color: var(--accent-dim); }
.description { margin: 0 0 18px; overflow-wrap: anywhere; color: #cfd3dd; }
.download {
  display: inline-block; background: var(--accent); color: #140a02; font-family: var(--display);
  font-size: 18px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  text-decoration: none; padding: 9px 22px; clip-path: var(--cut);
}
.download:hover { background: #ff9d45; }
.links { margin-top: 12px; font-size: 14px; color: var(--muted); }
.links a { margin-right: 14px; }
.unreleased { color: var(--muted); font-style: italic; margin: 0; }
.kind {
  font-family: var(--display); font-weight: 600; font-size: 16px; letter-spacing: 0.05em; text-transform: uppercase;
  text-decoration: none; color: var(--text); padding: 7px 14px; border: 1px solid var(--card-edge); background: #141824;
  clip-path: var(--cut);
}
.kind:hover { border-color: var(--accent-dim); color: var(--accent); }
.badge.waiting { color: #e6b24a; border-color: #6b5212; }
.install {
  margin-top: 36px; padding: 18px 22px; border-left: 3px solid var(--accent); background: #0e111a; color: #cfd3dd;
}
.install h3 { font-family: var(--title); margin: 0 0 6px; font-size: 17px; text-transform: uppercase; letter-spacing: 0.04em; font-weight: normal; color: var(--accent); }
.install p { margin: 0; }
code { background: #1a1f2c; padding: 1px 6px; border-radius: 4px; font-size: 14px; }
footer { color: var(--muted); font-size: 14px; margin-top: 28px; }
@media (max-width: 760px) { .mod { grid-template-columns: 1fr; } }

/* Browsing by category: where you are, the categories in it, and the search, sort and filter. */
.browse { margin-bottom: 22px; }
.crumbs ol { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; margin: 0 0 6px; padding: 0; list-style: none; font-family: var(--title); font-size: 22px; letter-spacing: 0.04em; text-transform: uppercase; }
.crumbs li + li::before { content: "/"; color: var(--accent-dim); margin-right: 10px; }
.crumbs a { color: var(--muted); text-decoration: none; }
.crumbs a:hover { color: var(--accent); }
.crumbs [aria-current] { color: var(--text); }
.about { margin: 0 0 14px; color: var(--muted); max-width: 640px; }
.kinds { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 18px; }
.kinds:empty { display: none; }
.kind .n { margin-left: 8px; color: var(--accent); }
.kind.none { color: var(--muted); }
.kind.none .n { color: var(--muted); }
.tools { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 18px; padding: 12px 14px; background: #0e111a; box-shadow: inset 0 0 0 1px var(--card-edge); }
.tools input[type="search"], .tools select {
  font: 15px system-ui, -apple-system, "Segoe UI", sans-serif; color: var(--text); background: #141824;
  border: 1px solid var(--card-edge); padding: 7px 10px;
}
.tools input[type="search"] { flex: 1 1 220px; min-width: 0; }
.tools input[type="search"]:focus, .tools select:focus { outline: none; border-color: var(--accent); }
.tools label { font-family: var(--display); font-weight: 600; font-size: 15px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); display: flex; align-items: center; gap: 8px; }
.count { margin: 14px 0 0; font-family: var(--display); font-weight: 600; font-size: 15px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
.empty { padding: 22px; color: var(--muted); background: #0e111a; box-shadow: inset 0 0 0 1px var(--card-edge); }
.empty p { margin: 0; }

/* The updates: each release, newest first. */
.updates { list-style: none; margin: 0; padding: 0; }
.update {
  display: grid; grid-template-columns: 120px 1fr; gap: 20px; padding: 18px 22px; margin-bottom: 16px;
  background: var(--brackets), linear-gradient(180deg, #141824, var(--card));
  background-repeat: no-repeat; box-shadow: inset 0 0 0 1px var(--card-edge);
}
.update img { display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: cover; background: #000; clip-path: var(--cut); }
.update h2 { font-family: var(--title); margin: 0 0 8px; font-size: 22px; line-height: 1.15; letter-spacing: 0.03em; text-transform: uppercase; font-weight: normal; display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; }
.update h2 a { color: var(--text); text-decoration: none; }
.update h2 a:hover { color: var(--accent); }
.when { font-family: var(--display); font-weight: 600; font-size: 15px; letter-spacing: 0.08em; color: var(--accent); margin: 0 0 2px; }
.changes { margin: 0; padding-left: 20px; color: #cfd3dd; }
.changes li { margin: 2px 0; }
@media (max-width: 520px) { .update { grid-template-columns: 1fr; } .update img { max-width: 200px; } }

/* The cards lead to the mods' pages. */
.shot a { display: block; }
.shot a:hover img, .shot a:focus-visible img { filter: brightness(1.15); }
.mod h2 a { color: var(--text); text-decoration: none; }
.mod h2 a:hover { color: var(--accent); }

/* A mod's page: its pictures, beside what it is and its download. */
.detail {
  display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 28px; padding: 22px; margin-bottom: 28px;
  background: var(--brackets), linear-gradient(180deg, #141824, var(--card));
  background-repeat: no-repeat; box-shadow: inset 0 0 0 1px var(--card-edge);
}
.detail h1 { font-size: clamp(30px, 5vw, 42px); }
.stage { position: relative; aspect-ratio: 4 / 3; background: #000; clip-path: var(--cut); }
.stage img { display: block; width: 100%; height: 100%; object-fit: contain; background: #000; }
.hint { margin: 8px 0 0; font-size: 14px; color: var(--muted); }
.hint:empty { display: none; }
.gallery { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.gallery button { padding: 0; width: 96px; border: 1px solid var(--card-edge); background: #000; cursor: pointer; }
.gallery button[aria-current="true"] { border-color: var(--accent); }
.gallery img { display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: cover; }
.facts { display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; margin: 0 0 20px; }
.facts dt { font-family: var(--display); font-weight: 600; font-size: 14px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); padding-top: 2px; }
.facts dd { margin: 0; overflow-wrap: anywhere; }
.notes { margin-top: 22px; }
.notes h2, .history h2 { font-family: var(--title); margin: 0 0 8px; font-size: 20px; letter-spacing: 0.04em; text-transform: uppercase; font-weight: normal; color: var(--accent); }
.notes ul { margin: 0; padding-left: 20px; color: #cfd3dd; }
.history { margin-top: 36px; }
.history .updates { margin-top: 12px; }
.history .update { grid-template-columns: 1fr; }
@media (max-width: 760px) { .detail { grid-template-columns: 1fr; } }
"""

# Browses the mods: the category, the search and the sort are in the address, as
# ?category=ships/fighters&q=viper&sort=updated, or sort=downloads, so a link keeps them. Without scripts the page
# lists every mod.
BROWSE_SCRIPT = """
(function () {
  const categories = JSON.parse(document.getElementById("categories").textContent);
  const byPath = new Map(categories.map((category) => [category.path, category]));
  const browse = document.querySelector(".browse");
  const list = document.querySelector(".mods");
  const cards = Array.from(list.querySelectorAll(".mod"));
  const crumbs = browse.querySelector(".crumbs ol");
  const about = browse.querySelector(".about");
  const kinds = browse.querySelector(".kinds");
  const search = document.getElementById("search");
  const sort = document.getElementById("sort");
  const count = browse.querySelector(".count");
  const empty = document.querySelector(".empty");
  const emptyText = empty.querySelector("p");
  const state = { category: "", q: "", sort: "name" };

  const inside = (path, category) => category === "" || path === category || path.startsWith(category + "/");
  const trail = (path) => {
    const found = [];
    for (let at = byPath.get(path); at; at = at.parent === null ? null : byPath.get(at.parent)) found.unshift(at);
    return found;
  };
  // The category's slashes are kept as they are, so that the address reads as the folders do.
  const address = (category) => {
    const parts = [];
    if (category) parts.push("category=" + encodeURIComponent(category).replace(/%2F/g, "/"));
    if (state.q) parts.push("q=" + encodeURIComponent(state.q));
    if (state.sort !== "name") parts.push("sort=" + state.sort);
    return parts.length ? "?" + parts.join("&") : location.pathname;
  };
  const read = () => {
    const query = new URLSearchParams(location.search);
    const category = query.get("category") || "";
    state.category = byPath.has(category) ? category : "";
    state.q = query.get("q") || "";
    state.sort = ["updated", "downloads"].includes(query.get("sort")) ? query.get("sort") : "name";
    search.value = state.q;
    sort.value = state.sort;
  };
  const go = (category) => {
    state.category = category;
    history.pushState(null, "", address(category));
    show();
  };
  const categoryLink = (category, text) => {
    const link = document.createElement("a");
    link.href = address(category.path);
    link.textContent = text;
    link.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
      event.preventDefault();
      go(category.path);
    });
    return link;
  };
  const plural = (n) => n === 1 ? "1 mod" : `${n} mods`;

  function show() {
    const here = byPath.get(state.category);
    crumbs.replaceChildren(...trail(state.category).map((category) => {
      const item = document.createElement("li");
      if (category === here) {
        const current = document.createElement("span");
        current.textContent = category.name;
        current.setAttribute("aria-current", "page");
        item.append(current);
      } else item.append(categoryLink(category, category.name));
      return item;
    }));
    about.textContent = here.text;
    kinds.replaceChildren(...categories.filter((category) => category.parent === here.path).map((category) => {
      const link = categoryLink(category, category.name);
      link.className = "kind" + (category.count === 0 ? " none" : "");
      link.setAttribute("aria-label", `${category.name}, ${plural(category.count).replace(/^0 mods$/, "no mods")}`);
      const n = document.createElement("span");
      n.className = "n";
      n.textContent = category.count;
      link.append(n);
      return link;
    }));
    const words = state.q.toLowerCase().split(/\\s+/).filter(Boolean);
    const shown = cards.filter((card) => {
      const fits = inside(card.dataset.category, state.category)
        && words.every((word) => card.dataset.text.includes(word));
      card.hidden = !fits;
      return fits;
    });
    const byName = (a, b) => a.dataset.name.localeCompare(b.dataset.name);
    const orders = {
      name: byName,
      updated: (a, b) => (b.dataset.updated || "").localeCompare(a.dataset.updated || "") || byName(a, b),
      downloads: (a, b) => Number(b.dataset.downloads) - Number(a.dataset.downloads) || byName(a, b),
    };
    const order = orders[state.sort];
    shown.sort(order).forEach((card) => list.append(card));
    count.textContent = shown.length ? plural(shown.length) : "";
    empty.hidden = shown.length > 0;
    const hereCount = cards.filter((card) => inside(card.dataset.category, state.category)).length;
    emptyText.replaceChildren();
    if (hereCount === 0) {
      emptyText.append("No mods here yet. Made one? ");
      const how = document.createElement("a");
      how.href = "https://github.com/OpenReliant/openreliant-mods#adding-a-mod";
      how.textContent = "Here's how to send it in";
      emptyText.append(how, ".");
    } else emptyText.append("No mods here match the search.");
    document.title = here.path ? `${here.name}: OpenReliant mods` : "OpenReliant mods";
  }

  search.addEventListener("input", () => { state.q = search.value.trim(); history.replaceState(null, "", address(state.category)); show(); });
  sort.addEventListener("change", () => { state.sort = sort.value; history.replaceState(null, "", address(state.category)); show(); });
  window.addEventListener("popstate", () => { read(); show(); });
  read();
  browse.hidden = false;
  show();
})();
"""


# A mod's page: its pictures take turns on the stage. Without scripts the page shows its first.
DETAIL_SCRIPT = """
(function () {
  const picture = document.querySelector(".stage img");
  const hint = document.querySelector(".hint");
  const name = document.querySelector("h1").textContent;
  const pictures = Array.from(document.querySelectorAll(".gallery button"));
  pictures.forEach((button) => button.addEventListener("click", () => {
    picture.src = button.dataset.src;
    picture.alt = button.dataset.alt;
    hint.textContent = button.dataset.alt === name ? "" : button.dataset.alt;
    pictures.forEach((each) => each.setAttribute("aria-current", String(each === button)));
  }));
})();
"""


def page(title: str, description: str, current: str, base: str, body: str, scripts: list[str]) -> str:
    """A page of the site, with the top bar's `current` link lit: `body` under it, then `scripts`.
    `base` leads from the page back to the site's top, such as ../ from updates/."""
    lit = lambda name: ' current' if name == current else ''
    script_tags = "".join(f"<script>{script}</script>" for script in scripts)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
<style>{STYLE}</style>
</head>
<body>
<main>
<nav class="top">
<a class="brand" href="https://openreliant.github.io/openreliant/">Open<span>Reliant</span></a>
<div class="links">
<a class="keep" href="https://openreliant.github.io/openreliant/#download">Download</a>
<a href="https://openreliant.github.io/openreliant/docs/">Docs</a>
<a class="keep{lit('mods')}" href="{base or './'}">Mods</a>
<a class="keep{lit('updates')}" href="{base}updates/">Updates</a>
<a href="https://github.com/{REPOSITORY}">GitHub</a>
</div>
</nav>
{body}
</main>
{script_tags}
</body>
</html>
"""


def latest_openreliant() -> dict | None:
    """OpenReliant's latest release, for its version, which says whether a mod waits for a newer
    one; None where it can't be read."""
    try:
        found = subprocess.run(
            ["gh", "release", "view", "--repo", "OpenReliant/openreliant", "--json", "tagName"],
            check=True, capture_output=True, text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return json.loads(found)


def mod_releases() -> list[dict]:
    """The mods' releases, newest first, each with its tag, its date, its notes and its assets, each
    with its name, size, sha256 digest and download count: from GitHub, or from the git tags,
    without notes or assets, where GitHub can't be read."""
    try:
        found = subprocess.run(
            ["gh", "api", f"repos/{REPOSITORY}/releases", "--paginate",
             "--jq", ".[] | select(.draft | not) | {tag: .tag_name, date: .published_at, notes: .body, "
                     "assets: [.assets[] | {name, size, digest, download_count}]}"],
            check=True, capture_output=True, text=True,
        ).stdout
        releases = [json.loads(line) for line in found.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        tags = git("tag", "--list", "--format=%(refname:short) %(creatordate:iso-strict)").splitlines()
        releases = [{"tag": tag, "date": date, "notes": "", "assets": []} for tag, date in (line.split(" ", 1) for line in tags if " " in line)]
    return sorted(releases, key=lambda release: release["date"], reverse=True)


def changes(notes: str) -> list[str]:
    """The changes a release's notes list, under their `## Changes` heading, each without its
    Conventional Commits type, as `1.3, a ship of its own` for `feat(viper): 1.3, a ship of its own`."""
    listed: list[str] = []
    under = False
    for line in (notes or "").splitlines():
        if line.startswith("## "):
            under = line.startswith("## Changes")
            continue
        if under and line.startswith("- "):
            listed.append(re.sub(r"^[a-z]+(\([^)]*\))?!?:\s*", "", line[2:].strip()))
    return listed


def trail_of(category: Category, by_path: dict[str, Category]) -> list[Category]:
    """The categories from the top down to `category`, without mods/ itself."""
    trail = []
    at: Category | None = category
    while at is not None and at.path:
        trail.insert(0, at)
        at = by_path.get(at.parent_path) if at.parent_path is not None else None
    return trail


def category_links(category: Category, by_path: dict[str, Category], base: str) -> list[str]:
    """Links to `category` and the categories it's in, from the top down."""
    return [f'<a href="{base}?category={html.escape(step.path)}">{html.escape(step.name)}</a>' for step in trail_of(category, by_path)]


def where(category: Category, by_path: dict[str, Category], base: str) -> str:
    """The category's place, as links to it and the categories it's in: Ships / Fighters."""
    return f'<p class="where">{" / ".join(category_links(category, by_path, base))}</p>'


def card(mod, by_path: dict[str, Category], release: dict | None, updated: str, downloads: int) -> str:
    text = html.escape
    picture = (f'<a href="{text(mod.page)}" aria-label="{text(mod.name)}: its page">'
               + (f'<img src="thumbs/{text(mod.id)}.png" alt="{text(mod.name)}">' if mod.thumbnail else '<img alt="">') + '</a>')
    badges = badges_of(mod, release, updated)
    details = f'<a href="{text(mod.page)}">Details</a>'
    if mod.released():
        download = (f'<a class="download" href="{text(mod.download())}">Download {text(mod.archive)}</a>'
                    f'<div class="links">{details}<a href="{text(mod.download())}.sha256">Checksum</a>'
                    f'<a href="{text(mod.release_page())}">Release notes</a>{links_of(mod)}</div>')
    else:
        download = f'<p class="unreleased">Not released yet.</p><div class="links">{details}{links_of(mod)}</div>'
    searched = " ".join([mod.name, mod.author, mod.description]).lower()
    data = (f'data-category="{text(mod.category)}" data-name="{text(mod.name.lower())}" data-updated="{text(updated)}" '
            f'data-downloads="{downloads}" data-text="{text(searched)}"')
    return (f'<article class="mod" {data}><div class="shot">{picture}</div><div>{where(by_path[mod.category], by_path, "")}'
            f'<h2><a href="{text(mod.page)}">{text(mod.name)}</a></h2><div class="badges">{badges}</div>'
            f'<p class="description">{text(mod.description)}</p>{download}</div></article>')


def badges_of(mod, release: dict | None, updated: str) -> str:
    """Its version, its author, the OpenReliant it needs and when it was last updated, as badges,
    and a note where it needs an OpenReliant newer than the latest release."""
    text = html.escape
    badges = [f'<span class="badge version">Version {text(mod.version)}</span>' if mod.version else "",
              f'<span class="badge">by {text(mod.author)}</span>' if mod.author else "",
              f'<span class="badge">Needs OpenReliant {text(mod.needs)}</span>' if mod.needs else "",
              f'<span class="badge">Updated {text(updated[:10])}</span>' if updated else ""]
    return "".join(badges) + waiting_badge(mod, release)


def waiting_badge(mod, release: dict | None) -> str:
    """A note where it needs an OpenReliant newer than the latest release."""
    if mod.needs and release and version_tuple(release["tagName"]) < version_tuple(mod.needs):
        return f'<span class="badge waiting">OpenReliant {html.escape(mod.needs)} is coming soon</span>'
    return ""


def waiting_of(mod, release: dict | None) -> str:
    """The waiting note as a mod's page shows it, in a row of its own."""
    badge = waiting_badge(mod, release)
    return f'<div class="badges">{badge}</div>' if badge else ""


def links_of(mod) -> str:
    """The links to its credits and licence, its source in an artist's repository, and its own
    website, where its manifest or its artist gives one other than this collection."""
    text = html.escape
    label, address = mod.credits()
    links = f'<a href="{text(address)}">{text(label)}</a>'
    if mod.artist and label != "Source":
        links += f'<a href="{text(mod.source_page())}">Source</a>'
    if mod.url and REPOSITORY not in mod.url:
        links += f'<a href="{text(mod.url)}">Website</a>'
    return links


def size_of(megabytes: float) -> str:
    return f"{megabytes:.1f} MB" if megabytes < 1000 else f"{megabytes / 1000:.2f} GB"


def tag_parts(tag: str) -> tuple[str, str]:
    """The mod a release's tag names, and its version: coyote-worn-v1.0 is coyote-worn's 1.0. A tag
    without a version gives an empty one."""
    mod_id, _, version = tag.rpartition("-v")
    return mod_id, version


def releases_of(mod, releases: list[dict]):
    """Its releases, in the order of `releases`, each with its version."""
    for release in releases:
        mod_id, version = tag_parts(release["tag"])
        if mod_id == mod.id and version:
            yield release, version


def downloads_of(mod, releases: list[dict]) -> int:
    """How many times its archive has been downloaded, over all its releases, as GitHub counts
    them. Its checksum file isn't counted: it comes with the archive, and the game writes its own."""
    return sum(asset.get("download_count", 0) for release, _ in releases_of(mod, releases)
               for asset in release["assets"] if asset["name"] == mod.archive)


def history(mod, releases: list[dict]) -> str:
    """Its releases, newest first, each with what changed."""
    text = html.escape
    entries = []
    for release, version in releases_of(mod, releases):
        items = "".join(f"<li>{text(change)}</li>" for change in changes(release["notes"]))
        download = f"https://github.com/{REPOSITORY}/releases/download/{release['tag']}/{mod.archive}"
        page_url = f"https://github.com/{REPOSITORY}/releases/tag/{release['tag']}"
        entries.append(
            f'<li class="update"><div><p class="when">{text(release["date"][:10])}</p>'
            f'<h2>Version {text(version)}</h2>' + (f'<ul class="changes">{items}</ul>' if items else "")
            + f'<div class="links"><a href="{text(download)}">Download</a><a href="{text(page_url)}">Release notes</a></div></div></li>')
    if not entries:
        return ""
    return f'<section class="history"><h2>Releases</h2><ol class="updates">{"".join(entries)}</ol></section>'


def mod_page(mod, by_path: dict[str, Category], release: dict | None, releases: list[dict], updated: str, built: str) -> str:
    """A mod's own page: its pictures; what it is and what it needs; its download and its total
    downloads; its artist's notes; how to install it; and its releases."""
    text = html.escape
    base = "../../"
    listing = mod.artist.listing(mod.files) if mod.artist else None
    # Its pictures: its screenshots, or for an artist's pack the in-game picture its catalogue
    # gives, from the artist's own site, then its thumbnail.
    pictures = [(path.name, f"{mod.name} in OpenReliant") for path in mod.screenshots()]
    if listing and mod.artist.url and listing.get("preview"):
        pictures.insert(0, (mod.artist.url + str(listing["preview"]), f"{mod.name} in OpenReliant"))
    if mod.thumbnail:
        pictures.append((f"{base}thumbs/{mod.id}.png", mod.name))
    first = pictures[0] if pictures else ("", "")
    gallery = ""
    if len(pictures) > 1:
        gallery = '<div class="gallery">' + "".join(
            f'<button type="button" data-src="{text(src)}" data-alt="{text(alt)}" aria-current="{str(at == 0).lower()}" aria-label="Show {text(alt)}">'
            f'<img src="{text(src)}" alt="" loading="lazy"></button>' for at, (src, alt) in enumerate(pictures)) + "</div>"
    stage = (f'<div class="stage"><img src="{text(first[0])}" alt="{text(first[1])}"></div>'
             f'<p class="hint">{text(first[1]) if first[1] != mod.name else ""}</p>{gallery}')

    facts = []
    if mod.version:
        facts.append(("Version", text(mod.version)))
    if mod.author:
        facts.append(("By", text(mod.author)))
    if mod.needs:
        facts.append(("Needs", f"OpenReliant {text(mod.needs)}"))
    facts.append(("Category", " / ".join(category_links(by_path[mod.category], by_path, base))))
    latest = next((found for found in releases if found["tag"] == mod.tag), None)
    if latest:
        size = next((asset["size"] for asset in latest.get("assets", []) if asset.get("name") == mod.archive), None)
        if size:
            facts.append(("Download", f"{size_of(size / 1_000_000)}, <code>{text(mod.archive)}</code>"))
        facts.append(("Released", text(latest["date"][:10])))
    # Left out until someone has downloaded it, and where GitHub couldn't be read.
    if downloads := downloads_of(mod, releases):
        facts.append(("Total downloads", f"{downloads:,}"))
    facts_list = "".join(f"<dt>{name}</dt><dd>{value}</dd>" for name, value in facts)

    if mod.released():
        download = (f'<a class="download" href="{text(mod.download())}">Download {text(mod.archive)}</a>'
                    f'<div class="links"><a href="{text(mod.download())}.sha256">Checksum</a>'
                    f'<a href="{text(mod.release_page())}">Release notes</a>{links_of(mod)}</div>')
    else:
        download = f'<p class="unreleased">Not released yet.</p><div class="links">{links_of(mod)}</div>'
    notes = ""
    if listing and listing.get("notes"):
        items = "".join(f"<li>{text(str(note))}</li>" for note in listing["notes"])
        notes = f'<section class="notes"><h2>Still to come</h2><ul>{items}</ul></section>'

    body = f"""<nav class="crumbs" aria-label="Category"><ol><li><a href="{base}">All mods</a></li>{crumbs_of(by_path[mod.category], by_path, base)}<li><span aria-current="page">{text(mod.name)}</span></li></ol></nav>
<article class="detail">
<div class="media">{stage}</div>
<div>
<h1>{text(mod.name)}</h1>
{waiting_of(mod, release)}
<p class="description">{text(mod.description)}</p>
<dl class="facts">{facts_list}</dl>
{download}
{notes}
</div>
</article>
<section class="install">
<h3>Installing it</h3>
<p>Download <code>{text(mod.archive)}</code> and <code>{text(mod.archive)}.sha256</code>, put both in the <code>mods</code> folder of your game folder, next to <code>resource.hog</code>, and turn the mod on in OpenReliant's mods screen.</p>
</section>
{history(mod, releases)}
<footer>
<p><a href="https://github.com/{REPOSITORY}">The mods' sources</a>, with each mod's credits and licence. Updated {text(built)}. Headings are set in Newtown, by Roger White, from Roger's Fonts.</p>
</footer>"""
    return page(f"{mod.name}: OpenReliant mods", mod.description or f"{mod.name}, a mod for OpenReliant.", "mods", base, body, [DETAIL_SCRIPT])


def crumbs_of(category: Category, by_path: dict[str, Category], base: str) -> str:
    """The categories down to `category`, as the breadcrumbs' items."""
    return "".join(f"<li>{link}</li>" for link in category_links(category, by_path, base))


def index_page(root: Category, release: dict | None, releases: list[dict], updated_at: dict[str, str], updated: str) -> str:
    text = html.escape
    by_path = {category.path: category for category in all_categories(root)}
    data = [{"path": category.path, "parent": category.parent_path, "name": "All mods" if not category.path else category.name,
             "text": category.text if category.path else "Every mod in the collection, by category.", "count": len(category.all_mods())}
            for category in all_categories(root)]
    mods = sorted(root.all_mods(), key=lambda mod: mod.name.lower())
    cards = "\n".join(card(mod, by_path, release, updated_at.get(mod.id, ""), downloads_of(mod, releases)) for mod in mods)
    # The categories for the script; "</" kept out, so that nothing in them can end the tag.
    categories = json.dumps(data).replace("</", "<\\/")
    body = f"""<header>
<h1>Mods</h1>
<p>Mods for <a href="https://openreliant.github.io/openreliant/">OpenReliant</a>, checked to work and to be free to share. You need OpenReliant and your own copy of StarLancer.</p>
</header>
<section class="browse" aria-label="Browse the mods" hidden>
<nav class="crumbs" aria-label="Category"><ol></ol></nav>
<p class="about"></p>
<div class="kinds"></div>
<div class="tools">
<input type="search" id="search" placeholder="Search the mods" aria-label="Search the mods">
<label>Sort <select id="sort"><option value="name">By name</option><option value="updated">Recently updated</option><option value="downloads">By downloads</option></select></label>
</div>
<p class="count" aria-live="polite"></p>
</section>
<div class="mods">
{cards}
</div>
<div class="empty" hidden><p></p></div>
<section class="install">
<h3>Installing a mod</h3>
<p>Download its <code>.hog</code> file and its <code>.hog.sha256</code> file, put both in the <code>mods</code> folder of your game folder, next to <code>resource.hog</code>, and turn the mod on in OpenReliant's mods screen. OpenReliant checks the archive against its checksum as it loads it.</p>
</section>
<footer>
<p><a href="https://github.com/{REPOSITORY}">The mods' sources</a>, with each mod's credits and licence. Updated {text(updated)}. Headings are set in Newtown, by Roger White, from Roger's Fonts.</p>
</footer>
<script type="application/json" id="categories">{categories}</script>"""
    return page("OpenReliant mods", "Mods for OpenReliant, checked to work and to be free to share.", "mods", "", body, [BROWSE_SCRIPT])


def updates_page(root: Category, releases: list[dict], updated: str) -> str:
    """Every mod's releases, newest first, with what changed in each."""
    text = html.escape
    by_path = {category.path: category for category in all_categories(root)}
    by_id = {mod.id: mod for mod in root.all_mods()}
    entries = []
    for release in releases:
        mod_id, version = tag_parts(release["tag"])
        mod = by_id.get(mod_id)
        # A mod that has left the collection keeps its releases on GitHub, not here.
        if mod is None or not version:
            continue
        listed = changes(release["notes"])
        items = "".join(f"<li>{text(change)}</li>" for change in listed)
        picture = (f'<a href="../{text(mod.page)}" tabindex="-1">' + (f'<img src="../thumbs/{text(mod.id)}.png" alt="">' if mod.thumbnail else '<img alt="">') + "</a>")
        download = f"https://github.com/{REPOSITORY}/releases/download/{release['tag']}/{mod.archive}"
        page_url = f"https://github.com/{REPOSITORY}/releases/tag/{release['tag']}"
        entries.append(
            f'<li class="update">{picture}<div><p class="when">{text(release["date"][:10])}</p>{where(by_path[mod.category], by_path, "../")}'
            f'<h2><a href="../{text(mod.page)}">{text(mod.name)}</a><span class="badge version">Version {text(version)}</span></h2>'
            + (f'<ul class="changes">{items}</ul>' if items else "")
            + f'<div class="links"><a href="{text(download)}">Download</a><a href="{text(page_url)}">Release notes</a></div></div></li>')
    listing = f'<ol class="updates">{"".join(entries)}</ol>' if entries else '<div class="empty"><p>No releases yet.</p></div>'
    body = f"""<header>
<h1>Updates</h1>
<p>Every mod's releases, newest first, with what changed in each.</p>
</header>
{listing}
<footer>
<p><a href="https://github.com/{REPOSITORY}/releases">Every release on GitHub</a>. Updated {text(updated)}. Headings are set in Newtown, by Roger White, from Roger's Fonts.</p>
</footer>"""
    return page("Updates: OpenReliant mods", "The latest releases of the mods for OpenReliant.", "updates", "../", body, [])


def index_json(mods: list[Mod], releases: list[dict], updated_at: dict[str, str], updated: str) -> str:
    """mods.json: every mod that has a release, in its latest version, with what its card shows, the
    link to its archive, and the archive's size and sha256 digest, which pin the exact archive the
    game installs. OpenReliant's GET MODS screen reads it to list and install the mods from the
    game. The game's documentation defines the keys (docs/guide/modding.md, "The catalogue's
    format"). Mods that aren't released yet, and keys without a value, are left out. So is a mod
    whose archive's size or digest isn't known, as when GitHub couldn't be read: the game would skip
    it anyway, and the message says which."""
    # Each asset's size and digest, by its release's tag and its name. GitHub writes the digest as
    # sha256:<hex>; the index keeps the hex digits.
    sizes: dict[tuple[str, str], int] = {}
    digests: dict[tuple[str, str], str] = {}
    for release in releases:
        for asset in release["assets"]:
            sizes[(release["tag"], asset["name"])] = asset["size"]
            if digest := asset.get("digest"):
                digests[(release["tag"], asset["name"])] = digest.removeprefix("sha256:")
    listed = []
    for mod in sorted(mods, key=lambda mod: mod.id):
        if not mod.released():
            continue
        size = sizes.get((mod.tag, mod.archive))
        digest = digests.get((mod.tag, mod.archive))
        if size is None or digest is None:
            print(f"mods.json leaves out {mod.id}: the size or the digest of {mod.archive} in {mod.tag} isn't known", file=sys.stderr)
            continue
        entry = {
            "id": mod.id,
            "name": mod.name,
            "category": mod.category,
            "version": mod.version,
            "author": mod.author,
            "description": mod.description,
            "openreliant": mod.needs,
            "updated": updated_at.get(mod.id, ""),
            "size": size,
            "archive": mod.download(),
            "sha256": digest,
            "thumbnail": f"{SITE_URL}thumbs/{mod.id}.png" if mod.thumbnail else None,
            "url": SITE_URL + mod.page,
        }
        listed.append({key: value for key, value in entry.items() if value not in ("", None)})
    return json.dumps({"format": INDEX_FORMAT, "generated": updated, "mods": listed}, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    root = tree()
    if found := problems(root):
        for problem in found:
            print(problem, file=sys.stderr)
        return 1
    shutil.rmtree(SITE, ignore_errors=True)
    (SITE / "thumbs").mkdir(parents=True)
    (SITE / "updates").mkdir()
    mods = root.all_mods()
    for mod in mods:
        if mod.thumbnail:
            shutil.copy(mod.thumbnail, SITE / "thumbs" / f"{mod.id}.png")
    release = latest_openreliant()
    releases = mod_releases()
    # Each mod's latest release's date, from the newest first.
    updated_at: dict[str, str] = {}
    for found_release in releases:
        updated_at.setdefault(tag_parts(found_release["tag"])[0], found_release["date"])
    updated = git("log", "-1", "--format=%cs")
    (SITE / "index.html").write_text(index_page(root, release, releases, updated_at, updated), encoding="utf-8")
    (SITE / "updates" / "index.html").write_text(updates_page(root, releases, updated), encoding="utf-8")
    (SITE / "mods.json").write_text(index_json(mods, releases, updated_at, updated), encoding="utf-8")
    by_path = {category.path: category for category in all_categories(root)}
    for mod in mods:
        folder = SITE / mod.page
        folder.mkdir(parents=True)
        for picture in mod.screenshots():
            shutil.copy(picture, folder / picture.name)
        (folder / "index.html").write_text(mod_page(mod, by_path, release, releases, updated_at.get(mod.id, ""), updated), encoding="utf-8")
    print(f"wrote {SITE / 'index.html'}, {SITE / 'updates' / 'index.html'}, {SITE / 'mods.json'} and a page for each mod: {len(mods)} mods, {len(releases)} releases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
