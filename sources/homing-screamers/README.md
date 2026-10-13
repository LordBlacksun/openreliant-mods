# Homing Screamers: sources

`homing.luau` is the mod's whole source, so there's nothing to build. It gives each of the
player's Screamers the player's target and sets its `homes`, so that OpenReliant's own missile
guidance (`home` in `src/engine/game/missiles.zig`) flies it as it flies the AI's. Its comments say
which Screamers it leaves alone, and why.

`mod.svg` is the mod's thumbnail, an original drawing of a missile curving onto a target in its
brackets. `mod.png` is made from it with ImageMagick 7:

```bash
magick -background none mod.svg ../../mods/gameplay/homing-screamers/mod.png
```
