# Writing a partner

A partner is the other painter. In the hosted copy inside claude.ai the built-in partner is Claude. Anywhere else you plug in your own,
which is also how you would add a comparison condition: a small model that continues strokes, a mirror that repeats the person's habits,
or a random painter as a control.

## Registering one

Before the page's script runs (or at any time before the person presses Start), put an object on `window.InkPartners`:

```html
<script>
  window.InkPartners = {
    mirror: {
      label: 'Mirror',
      async turn(ctx) {
        // look at ctx, decide, answer with gestures
        return { gestures: [{ type: 'pour', x: 0.5, y: 0.5, seconds: 1.2, path: [] }] };
      }
    }
  };
</script>
```

If more than one partner is registered, a selector appears next to the "Pass the paper" button. If none is, the button is hidden.

## What `turn(ctx)` receives

| Field | Meaning |
|---|---|
| `ctx.grid`, `ctx.cols`, `ctx.rows` | a coarse darkness map of the paper, `rows` lines of `cols` digits, 0 (blank) to 9 (black), top to bottom |
| `ctx.imageBlob` | a JPEG of the paper (480 px wide) |
| `ctx.aspect` | width divided by height of the sheet |
| `ctx.ink` | the partner's ink pot, 0 (clear water) to 1 (scorched) |
| `ctx.words` | the person's note (empty unless words are on and the person wrote something) |
| `ctx.strokes` | the person's recent strokes, or `null` unless "sees" is `paper+strokes`. Each has `start`, `seconds`, `pause`, `length` and `path` |
| `ctx.settings` | the friction settings in force |
| `ctx.history` | the partner's earlier gestures this session |
| `ctx.prompt` | a ready-made text prompt for a language model, built from all of the above |

It returns (or resolves to) `{ gestures: [...] }`. Throw an error with a `code` to report a failure; `rate_limited` and `not_granted` have friendly messages.

## Gestures

```json
{ "type": "pour", "x": 0.5, "y": 0.5, "seconds": 1.5, "path": [[0.55, 0.6], [0.6, 0.7]], "ink": 0.8 }
{ "type": "tilt", "dx": 0, "dy": 1, "seconds": 1.5 }
{ "type": "wait", "seconds": 2 }
```

* `pour`: hold the brush at (`x`, `y`) for `seconds` (0.3 to 4). The optional `path` drags it through those points. `ink` (0 to 1) is only used when ink is unlimited.
* `tilt`: tilt the paper toward (`dx`, `dy`), each -1 to 1, for 0.5 to 3 seconds.
* `wait`: pause for 0.5 to 4 seconds.

At most 6 gestures are used, and gestures stop being added once their durations pass about 16 seconds. Coordinates are clamped to the sheet.
A partner uses the same ink, paper and physics as the person. It cannot place ink directly, only move a brush.

## What happens next

The answer is stored in the session as a `pg` event and painted over the following ticks, so replays repeat it exactly.
The text you were sent is stored as a `pr` event unless you remove it from the file.

## Calling something outside the browser

A partner can call any service from its `turn` function. Keep in mind what that sends: the picture of the paper and, depending on
the friction settings, the person's words and strokes. For a study, say so in your consent text.
Browsers also block calls to other sites unless the site allows them (CORS), so a small proxy of your own is usually needed.
