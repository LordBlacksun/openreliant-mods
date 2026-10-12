"""The mods in mods/, read from their manifests, for the release and the site.

mods/ holds a folder for each category, and categories can hold categories of their own, such as
mods/ships/fighters. A folder with a mod.ini is a mod, and every other folder is a category. A category's README.md gives its name, as its first heading, and what goes in it, as its
first paragraph, and its links to its own categories set the order the site lists them in.

Artists can keep their packs in their own repositories. Each such repository is a submodule under
external/, pinned to a commit, with external/<artist>.ini beside it:

    [Artist]
    Name=KonCyptFysh
    Url=https://koncyptfysh.github.io/OpenReliant-Art-Packs/
    Catalog=catalog.json

    [Categories]
    Alliance Fighters=ships/fighters/alliance

Every folder of the repository with a mod.ini, under a top folder that [Categories] maps, is one
of the collection's mods, in the category it maps to. The mod is named after its folder, without
the order number before it and the version after it: 30-coyote-worn-v4 is coyote-worn. Where two
folders give one name, the one with the higher Version is the mod. Catalog, where the artist keeps
one, names a JSON file listing their packs, as KonCyptFysh's does; then only the packs it marks
available count, each by the folder its entry names for the mod (modFolder), so that the artist's
other folders with a mod.ini in a pack, such as a recipe or a test setup, don't, and a pack's page
on the site shows the in-game picture and the notes its entry gives. Name and Url stand in for a mod's Author and Url where its mod.ini leaves
them out. A new pack, or a new version of one, needs only the pin moved.

    python3 .github/scripts/mods.py lfs-includes --packs|--thumbnails

prints, for each submodule, the Git LFS files its mods need: every file of them, or their
thumbnails alone. The workflows fetch those and no others.
"""

from __future__ import annotations

import configparser
import functools
import json
import pathlib
import re
import subprocess
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODS = ROOT / "mods"
SOURCES = ROOT / "sources"
# The pictures a mod's page can show.
PICTURES = (".png", ".jpg", ".jpeg", ".webp")
EXTERNAL = ROOT / "external"
REPOSITORY = "OpenReliant/openreliant-mods"


def section(path: pathlib.Path, name: str, keep_case: bool = False) -> dict[str, str]:
    """The section `name` of the ini file at `path`, by its keys in lower case, or as written with
    `keep_case`; empty if there's none."""
    parsed = configparser.ConfigParser(delimiters=("=",), interpolation=None, strict=False, comment_prefixes=(";", "#"))
    if keep_case:
        parsed.optionxform = str  # type: ignore[assignment,method-assign]
    parsed.read(path, encoding="utf-8")
    return dict(parsed[name]) if parsed.has_section(name) else {}


class Artist:
    """An artist's repository: the submodule under external/ that holds it, pinned to a commit, and
    external/<artist>.ini, which says how its mods fit the collection."""

    def __init__(self, ini: pathlib.Path):
        self.ini = ini.relative_to(ROOT).as_posix()
        self.submodule = ini.with_suffix("").relative_to(ROOT).as_posix()
        self.root = ROOT / self.submodule
        about = section(ini, "Artist")
        self.name = about.get("name", "")
        self.url = about.get("url", "")
        self.catalog = about.get("catalog", "")
        # The collection's category for each top folder of the repository, by its name.
        self.categories = section(ini, "Categories", keep_case=True)

    def repository(self) -> str | None:
        """The repository's web address, as .gitmodules gives it; None if no submodule is there."""
        for line in git_lines("config", "-f", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$"):
            key, _, path = line.partition(" ")
            if path == self.submodule:
                return git("config", "-f", ".gitmodules", key.removesuffix(".path") + ".url").removesuffix(".git")
        return None

    def commit(self) -> str:
        """The commit the submodule is pinned to, as checked out."""
        return git("-C", str(self.root), "rev-parse", "HEAD")

    def link(self, kind: str, path: str) -> str:
        """The repository's web page for `path` at the pinned commit: `tree` for a folder, `blob`
        for a file."""
        return f"{self.repository()}/{kind}/{self.commit()}/{urllib.parse.quote(path)}"

    def mods(self) -> tuple[list[Mod], list[str]]:
        """The artist's mods, and what's wrong with how the repository fits the collection."""
        if self.repository() is None:
            return [], [f"{self.ini}: {self.submodule} isn't a submodule in .gitmodules"]
        if not self.root.is_dir() or not any(self.root.iterdir()):
            return [], [f"{self.ini}: {self.submodule} isn't checked out; run git submodule update --init"]
        problems: list[str] = []
        available = self.available(problems)
        named: dict[str, list[pathlib.Path]] = {}
        for manifest in sorted(self.root.rglob("mod.ini")):
            folder = manifest.parent
            inside = folder.relative_to(self.root).as_posix()
            if available is not None and not any(inside.startswith(pack + "/") and mod in (None, folder.name) for pack, mod in available):
                continue
            named.setdefault(mod_name(folder.name), []).append(folder)
        found: list[Mod] = []
        for name, folders in named.items():
            folders.sort(key=lambda folder: version_tuple(section(folder / "mod.ini", "Mod").get("version", "")), reverse=True)
            if len(folders) > 1 and version_of(folders[0]) == version_of(folders[1]):
                problems.append(f"{self.ini}: {folders[0].relative_to(ROOT)} and {folders[1].relative_to(ROOT)} have the same name and Version")
                continue
            top = folders[0].relative_to(self.root).parts[0]
            category = self.categories.get(top)
            if category is None:
                problems.append(f"{self.ini}: {name}, in {top}, which [Categories] maps to no category")
                continue
            found.append(Mod.kept(self, folders[0], name, category))
        return found, problems

    @functools.cached_property
    def listed(self) -> list[dict]:
        """The packs the artist's catalogue lists, as the catalogue gives them; none where there's no
        catalogue or it can't be read."""
        if not self.catalog:
            return []
        try:
            assets = json.loads((self.root / self.catalog).read_text(encoding="utf-8"))["assets"]
        except (OSError, ValueError, KeyError, TypeError):
            return []
        return [asset for asset in assets if isinstance(asset, dict)]

    def listing(self, files: pathlib.Path) -> dict | None:
        """The catalogue's entry for the pack whose mod is in `files`, if the catalogue lists it."""
        inside = files.relative_to(self.root).as_posix()
        for asset in self.listed:
            folder = str(asset.get("folder", "")).strip("/")
            if folder and inside.startswith(folder + "/"):
                return asset
        return None

    def available(self, problems: list[str]) -> list[tuple[str, str | None]] | None:
        """The packs the catalogue marks available, each as its folder and the name of its mod's
        folder in it (modFolder), or None where its entry names none, which counts every mod in the
        pack's folder; None where there's no catalogue."""
        if not self.catalog:
            return None
        try:
            listed = json.loads((self.root / self.catalog).read_text(encoding="utf-8"))
            return [(asset["folder"].strip("/"), asset.get("modFolder") or None) for asset in listed["assets"] if asset.get("status") == "available"]
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as err:
            problems.append(f"{self.ini}: {self.submodule}/{self.catalog} can't be read as a catalogue: {err}")
            return []


def mod_name(folder: str) -> str:
    """The name of a mod an artist keeps in `folder`: without the order number before it and the
    version after it, as coyote-worn for 30-coyote-worn-v4."""
    return re.sub(r"-v\d+$", "", re.sub(r"^\d+-", "", folder))


def version_of(folder: pathlib.Path) -> tuple[int, ...]:
    return version_tuple(section(folder / "mod.ini", "Mod").get("version", ""))


class Mod:
    """A mod: where it is in the categories, and the [Mod] section of its mod.ini. Its files are
    in its folder under mods/, or in an artist's repository (`Artist`). Keys can be written in any
    case."""

    def __init__(self, folder: pathlib.Path):
        # The folder's name is what the mod's things are named after, as viper:viper, and what its
        # archive is called.
        self.read(folder, folder.name, folder.parent.relative_to(MODS).as_posix(), None)

    @classmethod
    def kept(cls, artist: Artist, files: pathlib.Path, name: str, category: str) -> Mod:
        """A mod of `artist`'s, its files in `files`, named `name` in the category `category`."""
        mod = cls.__new__(cls)
        mod.read(files, name, category, artist)
        return mod

    def read(self, files: pathlib.Path, name: str, category: str, artist: Artist | None) -> None:
        self.files = files
        self.id = name
        # Where its files are in the repository, such as mods/ships/fighters/viper, and its
        # category's path, such as ships/fighters.
        self.path = files.relative_to(ROOT).as_posix()
        self.category = category
        self.artist = artist
        about = section(files / "mod.ini", "Mod")
        self.name = about.get("name", self.id)
        self.version = about.get("version", "")
        self.author = about.get("author", artist.name if artist else "")
        self.description = about.get("description", "")
        self.needs = about.get("openreliant", "")
        self.url = about.get("url", artist.url if artist else "")
        self.thumbnail = files / "mod.png" if (files / "mod.png").exists() else None

    def credits(self) -> tuple[str, str]:
        """Where its credits and licence are, as a link's text and address: its license.txt, or
        for an artist's mod, the licence or credits file of its folder or of the repository, else
        its folder."""
        if not self.artist:
            return "Credits and licence", f"https://github.com/{REPOSITORY}/blob/main/{self.path}/license.txt"
        pack = self.files.relative_to(self.artist.root)
        # A licence before credits, and the mod's own before the repository's.
        for pattern in (r"licen[cs]", r"credits"):
            for holder in (pack, pathlib.Path(".")):
                for name in sorted(entry.name for entry in (self.artist.root / holder).iterdir()):
                    if re.match(pattern, name, re.IGNORECASE):
                        return "Credits and licence", self.artist.link("blob", (holder / name).as_posix())
        return "Source", self.source_page()

    @property
    def page(self) -> str:
        """Its page on the site, from the site's top, such as mods/viper/."""
        return f"mods/{self.id}/"

    def screenshots(self) -> list[pathlib.Path]:
        """The pictures its page shows after its thumbnail: for a mod of the collection, those in
        sources/<mod>/screenshots, in the order of their names."""
        if self.artist:
            return []
        folder = SOURCES / self.id / "screenshots"
        if not folder.is_dir():
            return []
        return sorted(path for path in folder.iterdir() if path.suffix.lower() in PICTURES)

    def lfs_pointers(self) -> list[pathlib.Path]:
        """Its files that are still Git LFS pointers, whose contents weren't fetched."""
        return [path for path in sorted(self.files.rglob("*")) if path.is_file() and path.stat().st_size < 1024
                and path.read_bytes().startswith(b"version https://git-lfs.github.com/spec/")]

    def source_page(self) -> str:
        """For an artist's mod, its folder in their repository at the pinned commit."""
        assert self.artist is not None
        return self.artist.link("tree", self.files.relative_to(self.artist.root).as_posix())

    def kept_in(self) -> str:
        """For an artist's mod, the folder of their repository that holds its own, whose history
        covers its versions however its own folder was named."""
        assert self.artist is not None
        return self.files.parent.relative_to(self.artist.root).as_posix()
    @property
    def tag(self) -> str:
        """The release tag of its current version, such as viper-v1.0."""
        return f"{self.id}-v{self.version}"

    @property
    def archive(self) -> str:
        return f"{self.id}.hog"

    def released(self) -> bool:
        """Whether its current version has a release tag."""
        return tag_exists(self.tag)

    def download(self) -> str:
        return f"https://github.com/{REPOSITORY}/releases/download/{self.tag}/{self.archive}"

    def release_page(self) -> str:
        return f"https://github.com/{REPOSITORY}/releases/tag/{self.tag}"


class Category:
    """A folder of mods/ that isn't a mod: its path, such as ships/fighters ("" for mods/ itself),
    and the name and the text its README.md gives."""

    def __init__(self, folder: pathlib.Path):
        self.folder = folder
        self.path = folder.relative_to(MODS).as_posix() if folder != MODS else ""
        readme = folder / "README.md"
        lines = readme.read_text(encoding="utf-8").splitlines() if readme.exists() else []
        heading = next((line[2:].strip() for line in lines if line.startswith("# ")), None)
        self.name = heading or folder.name.replace("-", " ").capitalize()
        self.text = first_paragraph(lines)
        # The order its README lists its own categories in, by their folders' names.
        self.listed = [link.strip("/") for link in re.findall(r"\]\(([^)/]+)/?\)", "\n".join(lines))]
        self.children: list[Category] = []
        self.mods: list[Mod] = []
        # For mods/ itself, what's wrong with how the artists' repositories fit the collection.
        self.problems: list[str] = []

    @property
    def parent_path(self) -> str | None:
        """Its parent's path; None for mods/ itself."""
        if self.path == "":
            return None
        return self.path.rpartition("/")[0]

    def all_mods(self) -> list[Mod]:
        """Its mods and those of every category in it."""
        return self.mods + [mod for child in self.children for mod in child.all_mods()]


def first_paragraph(lines: list[str]) -> str:
    """The first paragraph after the heading, joined into one line."""
    paragraph: list[str] = []
    for line in lines:
        if line.startswith("#") or line.startswith("- "):
            if paragraph:
                break
            continue
        if not line.strip():
            if paragraph:
                break
            continue
        paragraph.append(line.strip())
    return " ".join(paragraph)


def tree() -> Category:
    """mods/ as a tree of categories, each with its mods and the artists' mods it holds, in the
    order the site lists them."""

    def walk(folder: pathlib.Path) -> Category:
        category = Category(folder)
        folders = sorted(entry for entry in folder.iterdir() if entry.is_dir())
        for entry in folders:
            if (entry / "mod.ini").exists():
                category.mods.append(Mod(entry))
            else:
                category.children.append(walk(entry))
        rank = {name: at for at, name in enumerate(category.listed)}
        category.children.sort(key=lambda child: (rank.get(child.folder.name, len(rank)), child.folder.name))
        return category

    root = walk(MODS)
    by_path = {category.path: category for category in all_categories(root)}
    for artist in artists():
        found, problems = artist.mods()
        root.problems += problems
        for mod in found:
            if mod.category in by_path:
                by_path[mod.category].mods.append(mod)
            else:
                root.problems.append(f"{artist.ini}: {mod.id} goes in {mod.category}, which isn't a category")
    for category in by_path.values():
        category.mods.sort(key=lambda mod: mod.id)
    return root


def artists() -> list[Artist]:
    """The artists whose repositories are submodules under external/, by their ini files."""
    return [Artist(ini) for ini in sorted(EXTERNAL.glob("*.ini"))] if EXTERNAL.is_dir() else []


def all_categories(root: Category) -> list[Category]:
    """Every category of the tree, `root` first, each before its own."""
    return [root] + [category for child in root.children for category in all_categories(child)]


def all_mods() -> list[Mod]:
    return tree().all_mods()


def problems(root: Category) -> list[str]:
    """What's wrong with the collection: a mod outside any category, an artist's repository that
    doesn't fit it, or two mods with one name, which their archives and their things are named
    after."""
    found = [f"{mod.path}: a mod goes in a category's folder, such as mods/ships/fighters" for mod in root.mods]
    found += root.problems
    seen: dict[str, str] = {}
    for mod in root.all_mods():
        if mod.id in seen:
            found.append(f"{mod.path}: {seen[mod.id]} has the same name, and a mod's name must be its own")
        seen.setdefault(mod.id, mod.path)
    return found


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def git_lines(*arguments: str) -> list[str]:
    """The lines git writes; none where it fails, as `git config` does for a key that's missing."""
    done = subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, text=True)
    return done.stdout.splitlines() if done.returncode == 0 else []


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.lstrip("v").split(".") if part.isdigit())


def lfs_includes(thumbnails: bool) -> dict[str, list[str]]:
    """For each artist's submodule, the Git LFS files its mods need: every file of their folders,
    or their thumbnails alone. The submodules must be checked out, their LFS files left as they
    are."""
    found: dict[str, list[str]] = {}
    for mod in tree().all_mods():
        if mod.artist:
            inside = mod.files.relative_to(mod.artist.root).as_posix()
            found.setdefault(mod.artist.submodule, []).append(f"{inside}/mod.png" if thumbnails else f"{inside}/**")
    return found


def tag_exists(tag: str) -> bool:
    return git("tag", "--list", tag) == tag


if __name__ == "__main__":
    if sys.argv[1:2] != ["lfs-includes"] or sys.argv[2:] not in (["--packs"], ["--thumbnails"]):
        sys.exit("usage: mods.py lfs-includes --packs|--thumbnails")
    for submodule, patterns in lfs_includes(sys.argv[2] == "--thumbnails").items():
        print(f"{submodule}\t{','.join(patterns)}")
