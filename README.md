# OpenReliant mods

Mods for [OpenReliant](https://github.com/OpenReliant/openreliant), the open-source reimplementation
of StarLancer's engine. Each mod here is checked by the OpenReliant maintainers: it works with the
OpenReliant version its manifest names, and its licence lets you share it.

You need OpenReliant and your own copy of StarLancer. No mod here holds the PC game's archives or its
files as they ship. Some art packs rework the game's own models and textures, StarLancer Prequel
Missions brings the free trial's two missions, with their lines and movies, and Cut Dreamcast
Missions restores four missions cut from the campaign, from the Dreamcast version's disc. They all
work over your copy of the game.

**[Browse and download the mods](https://openreliant.github.io/openreliant-mods/)**, by category,
each from its latest release, and see [the latest updates](https://openreliant.github.io/openreliant-mods/updates/).
The released mods are also listed as data in [`mods.json`](https://openreliant.github.io/openreliant-mods/mods.json),
which OpenReliant reads to list and install them from its mods screen.

## Mods

The site lists every mod, by category. They come from two places:

- [`mods/`](mods), a folder for each category, holds the mods made for the collection, such as the
  Viper Mk II in [`mods/ships/fighters/viper`](mods/ships/fighters/viper).
- [`external/`](external) holds the repositories of artists who keep their mods themselves, such as
  KonCyptFysh's [art packs](https://koncyptfysh.github.io/OpenReliant-Art-Packs/) of the Alliance's
  fighters ([Artists' repositories](#artists-repositories)).

## Installing a mod

Download the mod's `.hog` file and its `.hog.sha256` file from its latest release, and put both in
the `mods` folder of your game folder, next to `resource.hog`. Then turn it on in OpenReliant's mods
screen. OpenReliant checks the archive against its checksum as it loads it.

To try the latest changes before they're released, copy the mod's own folder into the same `mods`
folder instead, keeping its name: `mods/ships/fighters/viper` becomes `<game>/mods/viper`. The name
matters: the game and the mod's scripts know what a mod adds by it, such as `viper:viper` for the
Viper, and `viper.hog` gives the same names. For an artist's mod, copy its folder from their
repository, renamed as the collection calls the mod: `Alliance Fighters/Coyote/mods/30-coyote-worn-v4`
becomes `<game>/mods/coyote-worn`.

```text
StarLancer/
  resource.hog
  mods/
    viper/
      mod.ini
      viper.shp
      ...
```

OpenReliant's [modding guide](https://github.com/OpenReliant/openreliant/blob/main/docs/guide/modding.md)
says how mods work.

## Adding a mod

A mod is a folder with a `mod.ini`, in the folder of its category under [`mods/`](mods), such as
`mods/ships/fighters/viper`. The folder's name is the mod's name, which its archive and its things
are named after, so it must be the only mod of that name in the collection. Give it a `mod.png`
thumbnail and a `license.txt` with its credits and licence, and open a pull request. Pictures for
its page on the site go in `sources/<mod>/screenshots`, as PNG, JPEG or WebP files.

Every other folder under `mods/` is a category, and a category can hold categories of its own,
such as `ships/fighters/alliance`. Its `README.md` gives its name as its first heading and what goes
in it as the paragraph after, and links to its own categories in the order the site lists them. A
category with no mods yet still shows on the site, with none in it. To add a category, add a folder
with its `README.md`, and link to it from the README of the category it's in.

## Artists' repositories

An artist can keep their mods in a repository of their own, and the collection picks up every mod
there, packs it and releases it, without a copy of its files here.

### What the repository holds

- Each mod is a folder with a `mod.ini`, as OpenReliant's modding guide describes, a `mod.png`
  thumbnail, and its licence in a `license.txt` or `LICENSE` file. A licence or credits file at
  the top of the repository counts for every mod without one of its own.
- The mods' folders sit under top folders that group them, such as `Alliance Fighters`. Below that,
  any layout works.
- A mod's folder can carry an order number and a version in its name, as `30-coyote-worn-v4`. The
  collection names the mod without them, `coyote-worn`, so that its name stays the same from one
  version to the next. Where two folders give one name, the one with the higher `Version` is the
  mod.
- Big files can be in Git LFS. The collection fetches only the mods' own files.

### The catalogue

A repository that holds mods which aren't ready yet keeps a catalogue: a JSON file that lists its
mods and marks the ones that are out. The collection picks up only those. It reads two fields of
each entry of `assets`, and the rest of the file is the artist's own:

```json
{
  "assets": [
    { "folder": "Alliance Fighters/Coyote", "status": "available" },
    { "folder": "Alliance Fighters/Patriot", "status": "coming-soon" }
  ]
}
```

- `folder`: the folder of the repository that holds the mod's folder.
- `status`: `available` for a mod that's out. Any other status leaves the mod out until it changes.
- `preview` and `notes`, where an entry gives them: an in-game picture, by its path on the
  artist's site (`Url`), and a list of notes. The mod's page on the site shows them.

Without a catalogue, every mod of the repository is picked up.

### Adding an artist

The artist's repository goes in as a submodule under `external/`, pinned to a commit:

```sh
git submodule add https://github.com/<artist>/<repository>.git external/<artist>
```

`external/<artist>.ini` beside it says how the repository fits the collection: the artist's name
and web page, for the mods whose `mod.ini` leaves out `Author` and `Url`; the catalogue, if there is
one; and the collection's category for each top folder:

```ini
[Artist]
Name=KonCyptFysh
Url=https://koncyptfysh.github.io/OpenReliant-Art-Packs/
Catalog=catalog.json

[Categories]
Alliance Fighters=ships/fighters/alliance
Coalition Fighters=ships/fighters/coalition
```

The Check workflow fails for a mod under a top folder with no category, so that a new kind of mod
gets a place before it's released.

### Updates

Each day, Dependabot opens a pull request that moves each artist's pin to their latest commit, if
they have new commits. Once the Check workflow passes on it, the Dependabot workflow merges it and
publishes: a mod that's new, or whose `Version` went up, is released, and the site shows it. A
pull request from Dependabot that changes anything besides the pins waits for review. The artist
can also open a pull request that moves the pin themselves:

```sh
git -C external/<artist> pull origin main
git add external/<artist>
```

The workflows fetch the Git LFS files of the mods' own folders and no others, and cache them by the
pins, so that each pin costs the artist's LFS bandwidth once. The release notes list the artist's
commits to the mod since its last release. To work with the mods locally, check out the submodules
without their LFS files, then fetch the same files:

```sh
GIT_LFS_SKIP_SMUDGE=1 git submodule update --init
python3 .github/scripts/mods.py lfs-includes --packs | while IFS=$'\t' read -r submodule include; do
  git -C "$submodule" lfs pull --include "$include"
done
```

## Releasing a mod

A mod's version is the `Version` in its `mod.ini`. To release it, raise the version and push to
`main`. The Publish workflow then:

1. packs the mod's files into `<mod>.hog` with `sltool hog pack --checksum`, with
   `<mod>.hog.sha256` beside it. `sltool` comes from OpenReliant's latest release. To build it
   from a branch of OpenReliant instead, give that branch as the `source` of
   `.github/actions/sltool`;
2. publishes the release `<mod>-v<version>`, such as `viper-v1.0`, with both files attached and
   the commits that changed the mod since its last release as its notes;
3. rebuilds the [site](https://openreliant.github.io/openreliant-mods/): the mods by category, and
   [the updates](https://openreliant.github.io/openreliant-mods/updates/), every release with what
   changed in it, newest first.

A version that has a release already is left alone, so other changes to `main` release nothing. On
a pull request, the Check workflow packs every mod and builds the site, to catch a mod that doesn't
pack or isn't in a category. `python3 .github/scripts/release.py --dry-run` does the same locally,
into `dist/`, and `python3 .github/scripts/site.py` writes the site into `site/`.

## Sources

`sources/` holds what each mod was built from, with the steps to build it again, so that anyone can
change it.

## Licences

Each mod gives its licence in its folder, and its art keeps its author's licence. Everything else,
such as the manifests, scripts and build scripts, is under the Mozilla Public License 2.0
([LICENSE](LICENSE)).
