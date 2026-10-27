---
name: character-from-photo
description: >-
  Turn a photo or drawing of a character into an animated pixel-art desk-display
  theme (VIEWE 480×480 GIFs) without replacing the default robot. Use when the
  user uploads a photo, mascot, or drawing and wants that character as pixel art
  on the screen, firmware, or custom theme. Triggers include "foto", "personaje",
  "pixel art", "mi cara en la pantalla", "custom theme from image".
---

# Character from a photo

The default face stays in `themes/standard/`. A photo becomes a **new** theme under `themes/custom/<id>/` (gitignored). The desk panel only shows it after embed + flash.

Do not pixel-scale the photo onto the screen and call it done. Draw a sprite that reads as that character: same outer silhouette in every frame, colors taken from the photo, motion only in eyes, mouth, arms, and a small state prop.

## Steps

1. Pick a short theme id (`fox`, `mochi`). Never write into `themes/standard/`.
2. Make the pixel reference (this is the photo, reduced — look at it, do not ship it as the animation):

```bash
python3 scripts/pixelate_reference.py PHOTO.png --out themes/custom/<id>/src
```

3. Read `themes/custom/<id>/src/ref.png` and `palette.json`. Draw a posable sprite (about 48×48) in the photo's colors. Each state is a different pose, the same set as `scripts/build_character_sprites.py`. Never save the same picture for every state.
   - Names: `<state>-000.png`, `<state>-001.png`, … in `themes/custom/<id>/src/frames/`.
   - `idle`: bob + blink + Zzz (4 frames). `waiting`: head glances left/right. `thinking`: thought dots. `running_shell`: legs swap (walk) + speed lines. `running_mcp`: a tool spark, not the walk. `success`: smile pulses. `error`: three shake frames, then hold. `stop`: a real wave + a bit of confetti.
   - One body function with pose arguments (bob, head shift, leg offset, which arm is up). Do not paste one bitmap and nudge it.
4. Pack:

```bash
python3 scripts/pack_character_theme.py themes/custom/<id>/src/frames \
  --id <id> --name "Name" --background "#hex-from-palette"
```

5. Open one GIF (`themes/custom/<id>/assets/idle.gif`) and check the silhouette matches the photo. If it is a colored blob, redraw.
6. Tell the user the robot is unchanged. To preview: `CURSOR_AGENT_BEACON_THEME=<id>`. To put it on the VIEWE, only if they ask to flash:

```bash
python3 scripts/embed_theme_gifs.py --theme <id>
./scripts/flash-viewe.sh
```

`THEME|` on the serial port does not swap art. The panel plays whatever was embedded at flash time.
