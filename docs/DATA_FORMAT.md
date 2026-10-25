# Data formats

Three JSON formats, each versioned by a `format` field and described by a JSON Schema in [`schema/`](schema/).
Check a file with `python tools/validate.py yourfile.json`. Small synthetic examples are in [`../examples/`](../examples/).

| Format | Written by | What it holds |
|---|---|---|
| `splashed-ink-plan/v2` | Machine Copy | A painting taken apart into wash strokes, pours and lines, in painting order |
| `splashed-ink-session/v1` | Splashed Ink | Everything a person and a partner did on one sheet, tick by tick |
| `splashed-ink-lobes/v1` | Machine Copy (*Learn from many paintings*) | How painters outlined blots: lobes of wash and the lines around each, in the lobe's own frame |

Plans and sessions use the same coordinate conventions. x runs left to right and y top to bottom, both as fractions of the sheet (0 to 1).
Sizes (radius, width, path length) are fractions of the sheet's **short side**, so a file means the same thing on any screen.

---

## 1. Plan v2 (`splashed-ink-plan/v2`)

Produced by Machine Copy's **Export** button.

```jsonc
{
  "format": "splashed-ink-plan/v2",
  "source": "synthetic-fish",          // name of the analysed image, without extension
  "aspect": 0.7477,                    // width / height of the analysed image
  "paperSeed": 896466344,              // seed of the simulated paper the copy was painted on
  "sim": { "width": 80, "height": 107, "stepsPerSecond": 360 },
  "note": "...",                       // plain-language caveat, always present
  "brush": { "baseRadius": "0.05 x short side", "radius": "baseRadius x size", "waterPerStep": "..." },
  "washStrokes": [ { "dry": false, "points": [[x, y, radius, tone, dry], ...] } ],
  "washes":      [ { "x": 0.55, "y": 0.51, "radius": 0.05, "size": 0.5, "seconds": 0.94, "ink": 3.5 } ],
  "strokes":     [ { "points": [[x, y, width, density, dry], ...] } ],
  "sequenceColumns": ["dx","dy","width","ink","dry","pen_down","pen_up","end"],
  "sequence":    [ [dx, dy, width, ink, dry, pen_down, pen_up, end], ... ]
}
```

### Layers

The painting is split into two kinds of ink, painted in this order: wet ink first, then dry-brush strokes, then lines.

* **`washStrokes`** are broad strokes dragged along the middle of a wash, as wide as the wash is at each point.
  Each point is `[x, y, radius, tone, dry]`: `radius` is half the local width, `tone` is how dark the original is there (0 to 1),
  `dry` is how dry the brush runs (0 wet, 1 very dry).
  `dry: true` marks a stroke painted with little water so bristle marks and white gaps survive; `dry: false` is laid as wet ink.
* **`washes`** are round pours that fill what the strokes leave uncovered. `radius` is the area to cover.
  `size` and `seconds` are the brush size multiplier and hold time that, on blank paper, were measured to cover that radius.
  `ink` is the concentration handed to the brush. It is a simulation parameter and can exceed 1, so **do not read it as a tone**.
* **`strokes`** are the thin dark structures, each thinned to a centre line. Each point is `[x, y, width, density, dry]`.
  `width` was measured as twice the distance to the stroke's edge. `density` is the ink deposit density this line adds on top of
  whatever is under it; the tone it adds is `1 - exp(-1.05 * density)`. The first point is the thicker end.

### `sequence`

A flat list for sequence models. Every wash stroke, then every pour, then every line, in painting order. One row per point:

| column | meaning |
|---|---|
| `dx`, `dy` | movement from the previous row, in short sides (the first row moves from the top-left corner) |
| `width` | stroke width, or twice the radius for wash strokes and pours |
| `ink` | a **tone**, 0 to 1, for every kind of row |
| `dry` | 0 to 1 |
| `pen_down`, `pen_up` | in the style of Sketch-RNN's `stroke-5`: `pen_down` is 1 while the next movement draws, `pen_up` is 1 on the last point of a stroke |
| `end` | 1 on the very last row only |

A pour appears as a one-point stroke whose `width` is its diameter.

### What is measured and what is assumed

Be careful with any of these when you use the data for research.

| Field | Status |
|---|---|
| positions, widths, radii, tones | **measured** from the image, at the analysis resolution (`sim`), not at the image's own |
| `dry` on a line | **measured** from gaps along the stroke in the original image, plus an assumed fade toward the tip |
| `dry` on a wash stroke | an assumed fade toward the tip; the wet/dry choice is measured from width, darkness and streakiness |
| order of strokes | **heuristic**: light before dark, wet before dry, lines last. It is not the painter's real order |
| direction of a stroke | **heuristic**: from the thicker end |
| `size`, `seconds`, `ink` of a pour | **calibrated** against the simulator on blank paper, so they only mean something for this simulator |

---

## 2. Session v1 (`splashed-ink-session/v1`)

Produced by Splashed Ink. A session is a header plus a list of events. Replaying the events in order, at the ticks they carry,
reproduces the picture.

```jsonc
{
  "format": "splashed-ink-session/v1",
  "id": "si-muudujl4o1ik",
  "app": { "name": "splashed-ink", "version": "0.3.0" },
  "startedAt": "2026-10-04T22:18:45.544Z",
  "endedAt":   "2026-10-04T22:19:00.302Z",
  "tickRate": 60,                      // ticks per second, always 60
  "stepsPerTick": 6,                   // simulation steps per tick (see the "st" event)
  "seed": 860685031,                   // seeds the brush jitter
  "paperSeed": 883487786,              // seeds the paper
  "device": { "viewport": [390, 760], "dpr": 3, "sim": [243, 475], "touch": true, "tiltSensor": true, "lockedSettings": false },
  "settings": { "undo": "none", "drying": "normal", "ink": "normal", "words": "off", "sees": "paper", "redo": "final" },
  "endTick": 466,
  "summary": { ... },                  // see below
  "events": [ { "t": 0, "e": "k", "k": "undo", "v": "unlimited" }, ... ]
}
```

`settings` are the friction settings at the start (see [FRICTION.md](FRICTION.md)). Later changes appear as `k` events.
`device.sim` is the simulation grid the session was painted on. A replay uses that grid, not the replaying device's own.

### Events

Every event has `t` (the tick it applies at, counted from 0) and `e` (its type). Events are ordered by `t`.
Several events can share a tick; they apply in file order, before that tick's simulation steps run.

| `e` | fields | meaning |
|---|---|---|
| `pd` | `i`, `x`, `y`, `p` | a finger or pen goes down. `i` identifies the pointer (`u` plus the browser's id), `p` is pressure. It pours or draws with the brush, depending on the last `tl` event |
| `pm` | `i`, `x`, `y`, `p` | it moves. At most one per pointer per tick, and only when it moved |
| `pu` | `i` | it lifts |
| `tl` | `v` | the person switches tool: `pour`, `brush` or `line` (the outlining brush). A tool the current role does not allow is ignored. A session starts with the role's first tool: `pour` when you splash or anything goes, `line` when you outline. Changing `roles` to one that does not allow the current tool switches to that role's first tool |
| `g` | `x`, `y` | the person's tilt target changes (each axis -0.8 to 0.8; positive y tilts toward the bottom) |
| `k` | `k`, `v` | a friction setting changes |
| `st` | `n` | simulation steps per tick change, on devices that cannot keep up. Rare |
| `sh` | `s` | a new sheet of paper with seed `s` |
| `un` | | one undo happened (only recorded if something was undone) |
| `pot` | `c` | with unlimited ink, the person chose a tone `c` (0 clear water, 1 scorched) |
| `pa` | `partner`, `words?`, `sees` | the paper is passed to a partner. `words` is the person's note, if any |
| `pg` | `gestures` | the partner's answer, starting to be painted at this tick |
| `pe` | `code` | the partner could not take its turn |
| `rd` | | the partner's turn is undone, to be asked again |
| `pr` | `partner`, `prompt` | a record of what was sent to the partner. Not needed to replay |

A partner's `gestures` are `pour` (`x`, `y`, `seconds`, optional `path` of `[x, y]` points, optional `ink`),
`stroke` (`path` of 2 to 10 `[x, y]` points, `seconds`, optional `ink`: a line drawn with the brush),
`outline` (as `stroke`, plus optional `press`: a line drawn with the fine outlining brush),
`tilt` (`dx`, `dy`, `seconds`) and `wait` (`seconds`).
Their durations are turned into ticks, so a replay repeats them exactly.

### Replaying

```
reset the simulation to the header: grid device.sim, paper paperSeed, random stream seed, settings
tick = 0; i = 0
loop:
    while i < len(events) and events[i].t <= tick:  apply(events[i]); i += 1
    if i == len(events) and tick >= endTick: stop
    run one tick                       # partner gestures, tilt, ink pot, then stepsPerTick simulation steps
    tick += 1
```

Splashed Ink's **Replay** button does exactly this, and `window.__si.replayHeadless(session)` does it without drawing.
The scripted check in `tests/run_checks.py` replays a session containing strokes, tilt, setting changes, undo, a new sheet,
and two partner turns, and compares the two pictures pixel by pixel.

**Exact on the same device only.** The simulation runs in GPU floating point, which can differ slightly between devices and
browsers. On the device that made the session the replay is identical. On another device it follows the same strokes and
the same physics but may differ in small details. Treat cross-device replays as faithful, not bit-exact.

### Summary

`summary` is computed from the events when a session ends. Fields: `seconds`, `strokes`, `pourSeconds`, `pathLength`
(in screen widths), `firstStrokeAfterSeconds`, `medianPauseSeconds`, `longestPauseSeconds` (gaps between strokes),
`brushStrokes` and `outlineStrokes` (how many of the person's strokes used the brush or the outlining brush), `partnerOutlines` and `partnerSplashes` (the partner's outline gestures, and its pour and stroke gestures), `undos`, `partnerTurns`, `partnerRedos`, `partnerErrors`, `partnerGestureSeconds`, `wordsSent`, `newSheets`, `settingChanges`.
It is a convenience, not a substitute for analysing the events.

### Privacy

A session contains how someone drew, when they paused, and any words they sent a partner. Sessions stay in the browser's local
storage unless the person exports them. The Session panel's switch turns local saving off. `pr` events store the full text sent
to a language-model partner (and a short `note` from built-in partners, such as which paintings the Reader borrowed from); delete them from a file if that matters for your use.
If you collect sessions from participants, get consent and whatever approval your institution requires. This repository
does not do that for you.

---

## 3. Lobe library v1 (`splashed-ink-lobes/v1`)

Built by Machine Copy from many paintings, without painting them. Each painting's ink map is taken apart as for a copy
(washes and lines), the washes are cut into lobes ([how](INK_MODEL.md#washes-as-lobes-machine-copy)), and every line is split into
runs by the lobe it lies nearest to, within 1.2 half-widths plus 2 cells of that lobe's edge. Runs shorter than 3 cells are dropped.

```json
{ "format": "splashed-ink-lobes/v1",
  "paintings": [ { "title": "...", "artist": "Bada Shanren (Zhu Da)", "date": "...", "source": "The Metropolitan Museum of Art",
                   "url": "https://www.metmuseum.org/art/collection/search/...", "image": "...", "license": "CC0 (The Met Open Access)",
                   "aspect": 0.71, "lobes": 31, "lines": 140 } ],
  "lobes": [ { "p": 0, "f": [19 numbers], "lines": [ [[u, v, width], ...], ... ] } ] }
```

**The lobe frame.** The origin is the middle of the lobe's long axis (its principal direction). `u` runs along that axis, from -1 at
the fuller end to 1 at the thinner end, in half-lengths. `v` runs across it, in half-widths, positive toward the side with more ink.
`width` is the line's width in half-widths. Because both apps put a lobe in this frame the same way, a line stored here can be drawn
into any other lobe: stretched to its length and width, turned to its direction.

**Features** `f`, used to find similar lobes: the log of elongation (half-length over half-width), the lobe's width above and below
its axis at 8 places along it (in half-lengths), its mean tone (0 to 1), and the log of its half-length relative to the sheet's short side.
The Reader compares lobes by a weighted distance over these (elongation 1.6, profile 1 each, tone 0.8, size 0.5).

**Empty `lines`** means the painter left that lobe without lines. That is information too: the Reader sometimes leaves a lobe alone when
its nearest match was left alone.

**Rights.** The library holds no images, only shapes and line positions, but each painting is listed with its source and licence.
Libraries built with *Fetch public-domain paintings from The Met* use only works The Met marks public domain (CC0). For anything
added from your own files, `license` says it is unknown: check before sharing such a library.

---

## 4. Motif library v1 (`splashed-ink-motifs/v1`)

What the Reader draws. Each motif is a thing an ink painter makes out of a blot (a bird, a fish, a rock), as a list of lines in
the motif's own frame and in drawing order. The shipped library ([`data/motifs-v1.json`](../data/motifs-v1.json)) is built by
`tools/build_traced.py` from [`data/manual-traced.json`](../data/manual-traced.json): key strokes traced by hand from the
*Mustard Seed Garden Manual* (1935 edition, National Diet Library, public domain; pages fetched by `tools/fetch_manual.py`) and from
CC0 paintings at the Cleveland Museum of Art. Each traced motif names its source, its long axis (`head`, `tail`) and its half-width.

| Field | Meaning |
|---|---|
| `label`, `zh`, `note` | what it is |
| `kind` | `manual`: traced by hand, in drawing order. `wash` or `line`: read from a painting by Machine Copy (experimental) |
| `f` | LobeKit features of its outline (see lobes-v1); for traced motifs only the elongation (first value) is used |
| `lines` | `[u, v, width]` points, u along the long axis (-1 to 1), v across in half-widths, in drawing order |
| `parts` | what each line draws (beak, eye, back, ...) |
| `sketch` | how many of the first lines make the pale first sketch |
| `painting` | the source: title, artist, link, licence |

`data/motifs-annotations.json` (format `splashed-ink-motif-annotations/v1`) boxes 38 motifs in the curated paintings; reading them
automatically (`tools/build_motifs.py`) did not give lines a person could read as the thing, which is why the shipped motifs are traced.

