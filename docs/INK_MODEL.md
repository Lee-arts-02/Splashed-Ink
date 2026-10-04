# The ink model

A short description of what the simulator does, enough to reproduce it or to know where it stops being believable.
The code is in `apps/splashed-ink/index.html` (the `SIM` shader) and, in a slightly different form, in `apps/machine-copy/index.html`.

## State

One grid cell holds four numbers, stored in a floating-point texture:

| channel | name | meaning |
|---|---|---|
| r | `w` | water sitting on the paper |
| g | `ink` | ink dissolved in that water |
| b | `dep` | ink fixed into the paper (this is what you see as a mark) |
| a | `m` | how damp the paper itself is |

Each cell also has two fixed paper properties: `F`, a fibre value from a random texture, and `PM`, permeability, which varies
slowly across the sheet and with the fibres. They come from `paperSeed`.

## One simulation step (per cell)

1. **Flow.** For each of the four neighbours, water moves along the gradient of `w`, scaled by the mean permeability of the two cells
   (damper paper is more permeable) and by how much water can move (`w * smoothstep(0, 0.12, w)`). Tilting the paper adds a second
   term that pushes water downhill, but only where there is deep water (`w * smoothstep(0.1, 0.9, w)`). Ink travels with the water at the
   concentration of the cell it comes from.
2. **Brush.** Within a radius of the brush centre, water and ink are added with a falloff of `(1 - r/R)^1.5`, scaled by the fibre value.
3. **Absorption.** Some water soaks into the paper (`w` falls, `m` rises) and drags a share of the ink into `dep`.
4. **Drying.** `w` and `m` decay slowly. Ink in water is fixed into `dep` at a rate that is higher where the water is shallow and where
   its edge is steep. When `w` falls below a threshold, all remaining ink is fixed.
5. **Display.** Tone is `1 - exp(-(1.05 * dep + 0.75 * ink))`, drawn over a paper colour with the fibre texture.

The **drying** friction setting multiplies the decay rates and the threshold in step 4 (0.35, 1, 4, or a very large number for
"instant").

## Constants

`K = 0.9` (flow), `G = 1.2` (tilt), absorption `0.003`, water decay `0.00016` per step, moisture decay `0.00015`,
dry threshold `0.002`, brush water `POUR = 0.06` per step at the centre. Brush radius is `0.05` of the short side times a size multiplier.
These were tuned by eye against how splashed ink looks. They are not fitted to measurements of real ink.

## Brush recipes (Machine Copy)

Machine Copy paints with the same step function. The recipes below are what makes a thin line, a wet wash or a dry-brush stroke.

* **Round pour.** A held brush: water `POUR * min(size^2, 2.5)` per step for `seconds * 360` steps. A smaller brush carries less water.
  Which `size` and `seconds` give a wanted radius, and how much ink gives a wanted tone, are looked up from a calibration run on blank paper.
* **Line.** A brush moved 0.5 cell per step. Radius `0.75 * width`, water `0.0012 * radius^2` clamped to `[0.0022, 0.03]`,
  ink concentration set so the deposited density matches the original's. Tested against synthetic lines of known width and tone:
  the visible width was within about one cell and the density within about 0.05.
* **Wet wash stroke.** A wide brush moved 1.5 cells per step with extra water (`1.2` times a round pour's), so that neighbouring strokes merge.
* **Dry-brush stroke.** A very small amount of water (`0.0015` per step), a flat-bodied footprint instead of a peaked one, bristle streaks
  along the direction of travel (each streak lane gets a random amount of ink), and a fibre-dependent threshold so the paper's high
  fibres take ink and the rest do not. This is what leaves white gaps.

## What it does not do

* **No momentum.** Water spreads and runs downhill; it is never *thrown*. A fast stroke does not push ink ahead of the brush.
  Making ink rush and splash needs a velocity field. That is the biggest known gap.
* **No pigment mixing, no colour**, only one ink.
* **Resolution dependent.** Cells are about 1.6 screen pixels, and spreading is measured in cells, so the same picture at a different grid size
  looks different. Sessions store the grid they used for this reason.
* **Tilt barely moves shallow washes.** Flow under tilt needs deep water; the broad wash strokes of Machine Copy are too shallow for it.
