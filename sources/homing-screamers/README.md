# Homing Screamers: sources

`homing.luau` is the mod's whole source, so there's nothing to build. Its steering is OpenReliant's
own missile guidance, `home` and `steer` in `src/engine/game/missiles.zig`, with the same numbers;
its comments say where each one comes from, and how its Screamers differ from the AI's.

`mod.svg` is the mod's thumbnail, an original drawing of a missile curving onto a target in its
brackets. `mod.png` is made from it with ImageMagick 7:

```bash
magick -background none mod.svg ../../mods/gameplay/homing-screamers/mod.png
```
