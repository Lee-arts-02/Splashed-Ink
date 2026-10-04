# Friction settings

Splashed Ink has six settings. Each one adds or removes one kind of resistance between a person, the paper and a partner.
Open them with the **Friction** button, or fix them from the address bar (below).

The idea comes from two bodies of HCI work. Cox et al. argue that deliberately designed friction ("microboundaries") can interrupt
mindless interaction and invite reflection (*Design Frictions for Mindful Interactions: The Case for Microboundaries*, CHI EA 2016).
Chalmers and Galani's seamful design keeps the seams of a system visible and usable instead of hiding them (*Seamful interweaving*, DIS 2004).
Most generative tools are built to be as seamless as possible. This piece asks what a collaboration with a machine is like when the seams are the point.

## The settings

| Setting | Values | What it changes | What it takes away, or gives back |
|---|---|---|---|
| **Undo** | `none` · `one` · `unlimited` | none: nothing can be taken back. one: the last stroke. unlimited: up to 12 strokes, one after another | commitment. With unlimited undo, no single stroke needs to be decided |
| **Paper drying** | `slow` · `normal` · `fast` · `instant` | multiplies how fast water leaves the paper (0.35x, 1x, 4x, instant) | time. Slow paper keeps running and blooming; instant paper keeps exactly what you put down |
| **Ink supply** | `scarce` · `normal` · `unlimited` | scarce: the pot empties twice as fast and refills at half speed. normal: the original behaviour. unlimited: it never empties, and tapping the pot cycles tone | a limit that shapes rhythm. Unlimited ink brings back a tone picker |
| **Talking to your partner** | `off` · `on` | on: a text box appears before "Pass the paper". Up to 140 characters go to the partner | the rule that the only shared language is paint. With words on, you can specify instead of making |
| **What your partner sees** | `paper` · `paper+strokes` | paper: only the finished sheet. paper+strokes: also your recent strokes with their order, duration, pauses and paths | context. A painter arriving at a sheet sees only the sheet; with strokes the partner can read how you worked |
| **Your partner's turn** | `final` · `redo` | redo: an "Ask again" button undoes the partner's turn and asks once more | the permanence of the partner's act. Regenerating is how most generative tools work |

## Presets

* **Seamful** (the default) is the piece as designed: `undo none, drying normal, ink normal, words off, sees paper, redo final`.
* **Seamless** removes each resistance: `undo unlimited, drying instant, ink unlimited, words on, sees paper+strokes, redo redo`.

The two are ends of a scale, not a recommendation. Settings can be mixed freely, which is the useful part for comparing conditions.

## Setting conditions from the address bar

Parameters in the URL set the starting values. This is meant for running conditions in a study.

| Parameter | Example | Effect |
|---|---|---|
| `preset` | `?preset=seamless` | start from a preset |
| `undo`, `drying`, `ink`, `words`, `sees`, `redo` | `?undo=one&drying=fast` | set one setting. These override `preset` |
| `lock` | `?lock=1` | hide the Friction button so the person cannot change anything |
| `record` | `?record=0` | do not save sessions in the browser |

Example: `apps/splashed-ink/?undo=none&drying=normal&ink=normal&words=off&sees=paper&redo=final&lock=1`.
The settings in force are written into every session's header, and any change during play is a `k` event.

## Notes for study design

* The partner follows the same ink rules as the person. When ink is unlimited it may choose a tone for each pour, and when words are on it is
  told what you wrote, though it can only answer in paint. If undo is on, you can also undo the partner's turn.
* A person can end a session from the Session panel, which shows and saves a summary. Pauses, undos, re-asks and words sent are counted.
* Nothing here has been tested with participants. The settings are a way to build conditions, not a validated instrument.
