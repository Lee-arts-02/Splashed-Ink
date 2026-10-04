# Splashed Ink

Browser tools for painting splashed ink (泼墨) on a simulated sheet of paper, and for studying what changes when a machine is your
painting partner and the medium pushes back.

* **[Splashed Ink](apps/splashed-ink/)**: pour and tilt on a phone or computer. Pass the paper to a partner who answers only in ink.
  Six friction settings turn each kind of resistance up or down. Every session is recorded and can be replayed.
* **[Machine Copy](apps/machine-copy/)**: load an ink painting and the simulator copies it, using wet washes, dry-brush strokes and
  lines whose width it measures along their length. It exports what it found as data.

Everything runs in the browser from plain HTML files. There is no build step and nothing to install.

> An independent project. It is not affiliated with, or endorsed by, the MIT Media Lab or its Future Sketches group.

## Why

Most generative tools remove resistance: describe what you want, get a polished result, regenerate if you do not like it.
Three things quietly disappear: *making* (you specify instead), *commitment* (nothing is final) and *response* (you choose instead of reacting).
Splashed ink is nearly the opposite. You pour, you cannot fully control where it goes, and you respond to what it did.

This piece puts a machine at the other end of that process and makes the resistance adjustable, so it can be compared:
the same task with and without undo, with fast or slow paper, with or without words, with a partner that can or cannot be asked again.

## Try it

**Hosted.** Fork or clone this repository, set *Settings → Pages → Source* to *GitHub Actions*, and push to `main`. The included workflow publishes the site.

**Locally.**

```bash
python3 -m http.server 8000
# open http://localhost:8000/
```

On a phone, open the hosted address. Tilt needs a secure page (HTTPS or localhost). iPhone asks permission when you press *Lay the paper*.
Where there is no tilt sensor, drag the dot at the top right (or use the arrow keys on a computer).

## Splashed Ink

**Play.** Press and hold to pour. The more you pour, the paler the ink; pause and it darkens again. Tilt to let wet ink run.
Hold *new sheet* for a moment to start again. Pass the paper to a partner, who looks at it, then paints in the same ink with the same physics.
The partner never speaks; it answers with a few brush gestures.

**Friction.** The *Friction* button opens six settings. [Details and rationale in docs/FRICTION.md.](docs/FRICTION.md)

| Setting | From | To |
|---|---|---|
| Undo | none | unlimited |
| Paper drying | slow | instant |
| Ink supply | scarce | unlimited (with a tone picker) |
| Talking to your partner | ink only | words allowed |
| What your partner sees | the paper | paper and your strokes |
| Your partner's turn | final | can be asked again |

*Seamful* is the piece as designed. *Seamless* removes every resistance. Settings can be mixed.

**Sessions.** Every stroke, tilt, setting change and partner turn is recorded on a fixed 60-tick clock, kept in the browser, and can be exported as JSON.
The *Session* panel lists saved sessions, ends and summarises the current one (strokes, pauses, undos, partner turns), and replays any session at 1x, 4x or 16x.
Recording can be turned off. [Format in docs/DATA_FORMAT.md.](docs/DATA_FORMAT.md)

**Partners.** Inside claude.ai the built-in partner is Claude. Anywhere else, plug in your own with a few lines of JavaScript:
a model that continues strokes, a mirror of the person's habits, a random painter as a control.
[docs/PARTNER_API.md.](docs/PARTNER_API.md)

**Conditions for a study.** Settings can be fixed from the address bar, for example
`apps/splashed-ink/?undo=none&drying=normal&words=off&sees=paper&redo=final&lock=1`. Parameters are listed in [docs/FRICTION.md](docs/FRICTION.md).

## Machine Copy

Load a painting (a public-domain work from a museum's open-access collection is a good source) and press *Start copying*.

1. The painting is turned into a map of how much ink is where. Red seals are ignored.
2. It is split in two. **Washes** are ink wider than a brush line. **Strokes** are the thin dark structures left over: each is thinned to a centre line,
   and the distance to its edge gives its width at every point.
3. Washes are laid as broad strokes along their middle, as wide as the wash is there. A wash wider than one brush is split into parallel strokes.
   Wide, dark, smooth areas are painted wet; narrower or streakier ones are dragged dry so bristle marks and white gaps stay. Round pours fill what is left.
4. Lines are painted last, wide where the original is wide, thinning to the tip, and dry where the original shows gaps.
5. The middle panel shows what it found. **Export** writes it as data, ready for sequence models. [Format in docs/DATA_FORMAT.md.](docs/DATA_FORMAT.md)

The *Detail* menu trades speed for resolution (Fast, Standard, Fine).
[How the simulator and the brushes work: docs/INK_MODEL.md.](docs/INK_MODEL.md)

## Data

| Format | File | Schema | Example |
|---|---|---|---|
| Plan v2 (a painting taken apart) | written by Machine Copy | [`plan-v2.schema.json`](docs/schema/plan-v2.schema.json) | [`examples/plan-example.json`](examples/plan-example.json) |
| Session v1 (a recorded sitting) | written by Splashed Ink | [`session-v1.schema.json`](docs/schema/session-v1.schema.json) | [`examples/session-example.json`](examples/session-example.json) |

Both examples are synthetic. No painting is included in this repository. Check any file with `python tools/validate.py file.json`.

## Checking that it works

```bash
pip install playwright jsonschema
playwright install chromium
python tests/run_checks.py
```

The checks record a scripted session and replay it, compare the two pictures pixel by pixel, test that each friction setting does what it says,
test what a partner is and is not told, and run Machine Copy end to end on a synthetic image. They use software rendering so they also run without a GPU.
They take a few minutes.

## What to know before relying on it

* **Replays are exact on the device that made them.** The simulation uses GPU floating point, which can differ slightly between devices.
  Across devices a replay follows the same strokes and physics but may differ in small details.
* **The ink model is tuned by eye**, not fitted to real ink. It has no momentum: ink spreads and runs downhill but is never thrown.
  Making ink rush ahead of a fast stroke would need a velocity field, which is the main thing missing. [Limits in docs/INK_MODEL.md.](docs/INK_MODEL.md)
* **Machine Copy infers; it does not recover.** Stroke order and direction are heuristics, not the painter's real order. Positions, widths and tones
  are measured at the analysis resolution, not the image's own. The "percent of the way there" figure is a pixel-by-pixel score that favours matching broad tone
  and under-rewards fine lines. The data file says which fields are measured and which are assumed.
* **Verification status.** The checks above cover determinism, the friction settings, the data formats and an end-to-end Machine Copy run on a synthetic image.
  Machine Copy's Standard and Fine detail levels on real paintings were checked on cropped regions and at low resolution, not end to end at full size,
  and the wet/dry classification and dry-brush look have not been tested across many paintings. Please report what you see.
* **Nothing has been tested with participants.** The friction settings are a way to build conditions, not a validated instrument.
  Sessions record how someone drew, when they paused, and any words they sent. If you collect them, get consent and any approval your institution requires.
* **Paintings.** Do not add paintings you do not have the right to use. Many museums publish public-domain images under open-access terms; check each one.
  The example data here comes from an image the project generated.
* **Fonts** are loaded from Google Fonts. Offline, the pages fall back to system serif fonts.

## Roadmap

* Pull the ink simulation into one small shared library; the two apps currently carry slightly different copies of the step function.
* Add momentum to the simulation so ink can be thrown and rush ahead of a stroke. Splashed Ink would gain the most.
* Give Splashed Ink the stroke vocabulary Machine Copy extracts: lines of varying width, dry brush.
* Comparison partners: a small sequence model trained on exported plans, and a mirror that repeats the person's own habits.
* A Chinese-language interface.

## Related work and ideas this builds on

* Strassmann, *Hairy brushes*, SIGGRAPH 1986: a brush, a stroke (position and pressure), a dip and a paper as separate parts.
* Chu and Tai, *MoXi: Real-time ink dispersion in absorbent paper*, ACM TOG 2005: physically based ink spreading in paper.
* Xu et al., *Animating Chinese paintings through stroke-based decomposition*, ACM TOG 2006; Tang et al., *Animated construction of Chinese brush paintings*, IEEE TVCG 2018: taking strokes and their order out of a painting.
* Zhang et al., *Computational approaches for traditional Chinese painting: from the "Six Principles of Painting" perspective*, JCST 2024: a survey, including the lack of open datasets.
* Ha and Eck, *A neural representation of sketch drawings* (Sketch-RNN): the stroke format the `sequence` field follows.
* Lingdong Huang's [{Shan, Shui}\*](https://github.com/LingDong-/shan-shui-inf): procedural Chinese landscape painting as code.
* Cox, Gould, Cecchinato, Iacovides and Renfree, *Design frictions for mindful interactions: the case for microboundaries*, CHI EA 2016.
* Chalmers and Galani, *Seamful interweaving: heterogeneity in the theory and design of interactive systems*, DIS 2004.
* *Better slow than sorry: introducing positive friction for reliable dialogue systems*, arXiv:2501.17348.

## License

[MIT](LICENSE). Copyright (c) 2026 Li Jiang.
