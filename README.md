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
Switch **Tool** to *Brush* (or press B; P for pour) to draw lines. The brush is thick, wet and dark when you move it slowly and thin, dry and pale when you move it fast, and it runs out of ink as it travels; lift it and pause to dip again. Hold *new sheet* for a moment to start again. Pass the paper to a partner, who looks at it, then paints in the same ink with the same physics.
The partner never speaks; it answers with a few brush gestures.

**泼 and 勾: splash, then outline.** In splashed-ink painting the splash is chance and the outline reads it: the painter looks at the blot, decides it is a leaf or a rock, and draws it out with a few fine lines, never the whole edge. Splashed Ink splits those two hands between you and your partner. By default you splash (pour and brush) and your partner outlines; switch *Who does what* to have your partner splash and you outline with the fine brush (O). Wet paper shows a cool sheen that fades as it dries, so when you outline is a choice: into wet ink the line blooms, on dry paper it stays crisp.

**Friction.** The *Friction* button opens seven settings. [Details and rationale in docs/FRICTION.md.](docs/FRICTION.md)

| Setting | From | To |
|---|---|---|
| Who does what | you splash, partner outlines (or the reverse) | anything goes |
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

**Partners.** Five simple partners are built in and need no backend. They are rules, not AI, and are labelled that way:
*Reader* outlines what you splashed: it finds the lobes in your ink and, given a lobe library, borrows how painters outlined the most similar lobes (without one it falls back on simple rules: part of an edge, a vein, a stalk); *Splasher* pours for you to read;
*Chance* answers at random and reads nothing; *Counterweight* reads the paper and paints on the opposite side, then tilts toward the ink;
*Echo* mirrors your last stroke, but only when "What your partner sees" lets it see how you drew. Inside claude.ai, Claude appears first in the list.
To add your own with a few lines of JavaScript (a model that continues strokes, a mirror of the person's habits), see [docs/PARTNER_API.md](docs/PARTNER_API.md).
On GitHub Pages there is no Claude partner, only these.

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

**Learning from many paintings.** Below the copy, *Learn from many paintings* reads paintings without painting them and records
how each painter answered a blot of ink: every lobe of wash, put in its own frame (along its long axis, from the fuller end), with
the lines drawn in and around it. *Fetch public-domain paintings* looks up xieyi painters (Bada Shanren, Xu Wei, Shitao, Chen Chun,
Huang Shen, Xugu and others) in the open-access (CC0) collections of the Cleveland Museum of Art and The Met, keeps only ink paintings
marked public domain, and reads them in your browser. If nothing arrives, the status line counts each step (search, records, filter,
images) so you can see where it stopped. Museums' image servers usually refuse to let another web page read
their pixels, so the reliable way is the repository's **Build lobe library** workflow (`tools/build_library.py`): it downloads the
same CC0 paintings on GitHub's servers, reads each with Machine Copy in a headless browser, and uploads `data/lobes-v1.json` with a list
of every painting it used (`data/lobes-v1-sources.md`). Run it from the Actions tab. *Add your own images* does the same for files. *Export library* writes `lobes-v1.json`. Load it in Splashed Ink
(Session, *Load a lobe library*) or put it at `data/lobes-v1.json` in the repository, and the Reader partner outlines your ink by
finding the most similar lobes and borrowing how they were drawn, instead of following rules. Only shapes, line positions and each
painting's title, artist and source are kept; no image is stored.
[How the simulator and the brushes work: docs/INK_MODEL.md.](docs/INK_MODEL.md)

## Data

| Format | File | Schema | Example |
|---|---|---|---|
| Plan v2 (a painting taken apart) | written by Machine Copy | [`plan-v2.schema.json`](docs/schema/plan-v2.schema.json) | [`examples/plan-example.json`](examples/plan-example.json) |
| Session v1 (a recorded sitting) | written by Splashed Ink | [`session-v1.schema.json`](docs/schema/session-v1.schema.json) | [`examples/session-example.json`](examples/session-example.json) |
| Lobe library v1 (how painters outline blots) | written by Machine Copy, read by Splashed Ink's Reader; the shipped one is [`data/lobes-v1.json`](data/lobes-v1-sources.md) | [`lobes-v1.schema.json`](docs/schema/lobes-v1.schema.json) | [`examples/lobes-example.json`](examples/lobes-example.json) |

The examples are synthetic. No painting is included in this repository. Check any file with `python tools/validate.py file.json`.

## Checking that it works

```bash
pip install playwright jsonschema
playwright install chromium
python tests/run_checks.py
```

The checks record a scripted session and replay it, compare the two pictures pixel by pixel, test that each friction setting does what it says,
test that the brush gets wider and wetter the slower it moves, spends ink by distance and refills when lifted, test what a partner is and is not told,
and run Machine Copy end to end on a synthetic image. They use software rendering so they also run without a GPU, which makes them slow:
run `python tests/run_checks.py --splashed` and `--machine-copy` separately if you prefer.

## What to know before relying on it

* **Replays are exact on the device that made them.** The simulation uses GPU floating point, which can differ slightly between devices.
  Across devices a replay follows the same strokes and physics but may differ in small details.
* **The ink model is tuned by eye**, not fitted to real ink. It has no momentum: ink spreads and runs downhill but is never thrown.
  Making ink rush ahead of a fast stroke would need a velocity field, which is the main thing missing. [Limits in docs/INK_MODEL.md.](docs/INK_MODEL.md)
* **Machine Copy infers; it does not recover.** Stroke order and direction are heuristics, not the painter's real order. Positions, widths and tones
  are measured at the analysis resolution, not the image's own. When a copy finishes it reports two numbers instead of one: tone error (mean difference where
  either image has ink, split into too dark and too light) and line recall/precision (centrelines of the copy matched against the original's within
  about 1.5 cells). A single pixel score favoured broad tone and hid lost lines.
  **Refine tone** repaints with the ink corrected from the last attempt; it fixes overall too-dark and too-light areas, not edges. The data file says which fields are measured and which are assumed.
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
* More paintings in the library. The first one (`data/lobes-v1.json`, [list](data/lobes-v1-sources.md)) has 39 works, all from the Cleveland Museum of Art; The Met's API returned nothing to GitHub's servers. Some works in it are fine-line rather than splashed (Shen Zhou's Tiger Hill album, Liang Kai's Sericulture); a curated list would sharpen what the Reader learns.
* Lines in the library come out of Machine Copy in fragments (its centre lines break at junctions). Joining them would let the Reader borrow whole gestures. After that, a sequence model conditioned on the lobe instead of nearest neighbours.
* Comparison partners: a mirror that repeats the person's own habits.
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
