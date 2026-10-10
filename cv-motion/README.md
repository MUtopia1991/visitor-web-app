# CV Motion Studio

A 60-second animated CV for Mohammad Nasravi, built 100% in code.
Every platform, prop, logo board and the voxel twin is drawn procedurally on a
canvas; the soundtrack is synthesised from scratch; nothing is an AI-generated image.

```
cv-motion/
├── config.js      ← ALL the settings (name, headline, colours, character, career stops, timing)
├── studio.html    ← the motion engine + a preview tool with a settings panel
├── render.mjs     ← deterministic frame-by-frame MP4 renderer (Playwright + ffmpeg)
├── music.mjs      ← procedural lo-fi soundtrack, synced to the build animation
├── fonts/         ← Space Grotesk (display); Inter is used for body text
└── output/        ← rendered video
```

## Preview and tweak

Open `studio.html` in a browser (a local server is nicest: `npx serve .` then
<http://localhost:3000/studio.html>). The left panel exposes the settings in
`config.js`:

- **Person** – name, headline, location, tagline, badge.
- **Voxel twin** – skin, hair, beard on/off, glasses on/off, shirt/trousers/shoe colours.
- **Theme** – accent, background gradient, glow, walkway colour.
- **Timing** – total duration, intro/outro length, camera transition.
- **Stops** – one per career chapter: years, title, organisation, board text, colour,
  prop (`antenna`, `books`, `desk`, `tower`, `globe`, `chocolate`, `toolkit`) and bullet points.
- **Outro** – closing line and link chips.

Hit **Apply settings** to rebuild the world, scrub the timeline, or press **Download config.js**
to save your settings. Changing a colour, a title or a headline never means re-rendering
"and hoping" – the same settings always produce the same frames.

## Render the MP4

```bash
cd cv-motion
npm install            # installs Playwright (Chromium is downloaded on first install)
node render.mjs        # → output/mohammad-nasravi-cv.mp4  (1920×1080, 30 fps, H.264 + AAC)

# options
node render.mjs --workers 4             # parallel headless pages (default: min(4, CPU cores))
node render.mjs --seconds 12 --out output/preview.mp4   # quick preview of the opening
node render.mjs --no-audio
node render.mjs --crf 16                # higher quality / bigger file
```

`ffmpeg` must be on your PATH. Rendering is deterministic: the engine exposes a pure
`renderFrame(t)` and the renderer asks for every frame at `t = n / fps`, so the output does not
depend on machine speed.

## How it works

- **Isometric voxel engine** – blocks are projected with a classic 2:1 isometric transform and
  painter-sorted by `x + y + z`. Each block gets a spawn time, so platforms, props, boards and the
  twin fall into place block by block ("like Lego").
- **Text on voxel faces** – logo boards and labels are drawn directly onto block faces with an
  affine transform, so they sit in the 3D world.
- **Camera** – eases between stops; the outro pulls back to reveal the whole career world.
- **Soundtrack** – `music.mjs` synthesises pad, keys, bass, arpeggio and drums at 100 BPM and
  adds a pitched "tick" for every block that lands, using the exact build schedule the
  engine exports (`CV_STUDIO.events()`), plus a chime when the twin's head lands.

## Reuse it for another CV

Edit `config.js` only. Add or remove entries in `stops` (the timeline, walkways and
camera adapt automatically), pick a prop for each one, and re-render.
