"""Charcoal hints (柳炭): faint suggestions of what a blot of ink could be, for a person to accept, ignore or contradict.

Used by tools/charcoal_hints.ipynb. Two sources of suggestion, for comparison:
  * generated: a Stable Diffusion 1.5 + Mustard Seed Garden LoRA reads each blot (img2img from the blot), and the lines
    it draws are kept;
  * retrieved: the manual motif whose silhouette best fits the blot, scaled into it.
Either way the result is a transparent PNG the size of the paper, in a warm grey like willow charcoal. Splashed Ink loads
it as a layer that fades away; it never becomes ink.
"""
import io, json, os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

CHARCOAL = (112, 98, 84)


# ---------- the paper ----------
def load_paper(path_or_img):
    """Tone map (0 = paper, 1 = black ink) of an image exported from Splashed Ink, and the RGB image."""
    im = Image.open(path_or_img).convert("RGB") if not isinstance(path_or_img, Image.Image) else path_or_img.convert("RGB")
    g = ndi.gaussian_filter(np.asarray(im.convert("L"), np.float32), max(1.0, 0.003 * max(im.size)))   # smooth away the paper's fibre
    paper = np.percentile(g, 70); ink = min(np.percentile(g, 0.5), paper - 40)
    T = np.clip((paper - g) / max(30.0, paper - ink), 0, 1)
    return T, im


def find_blots(T, min_frac=0.0015, thr=0.15):
    """Each blot of ink: its mask and bounding box (x0, y0, x1, y1), largest first."""
    H, W = T.shape
    lab, n = ndi.label(ndi.binary_dilation(T > thr, iterations=max(2, int(0.006 * max(H, W)))))
    out = []
    for j, s in enumerate(ndi.find_objects(lab), 1):
        m = (lab[s] == j) & (T[s] > thr)
        if m.sum() < min_frac * H * W: continue
        out.append({"mask": m, "box": (s[1].start, s[0].start, s[1].stop, s[0].stop), "area": int(m.sum())})
    return sorted(out, key=lambda b: -b["area"])


def square_crop(T, box, margin=0.25):
    """A square around a blot, with room around it for a reading to reach past the ink."""
    H, W = T.shape; x0, y0, x1, y1 = box; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; s = max(x1 - x0, y1 - y0) * (1 + 2 * margin)
    X0, Y0 = int(round(cx - s / 2)), int(round(cy - s / 2)); X1, Y1 = X0 + int(round(s)), Y0 + int(round(s))
    pad = np.zeros((Y1 - Y0, X1 - X0), np.float32)
    sx0, sy0, sx1, sy1 = max(0, X0), max(0, Y0), min(W, X1), min(H, Y1)
    pad[sy0 - Y0:sy1 - Y0, sx0 - X0:sx1 - X0] = T[sy0:sy1, sx0:sx1]
    return pad, (X0, Y0, X1, Y1)


def to_model_image(crop, size=512):
    """The blot as the model sees it: dark ink on white, like the manual's prints."""
    g = (255 * (1 - np.clip(crop, 0, 1))).astype(np.uint8)
    return Image.fromarray(g).resize((size, size), Image.BICUBIC).convert("RGB")


# ---------- reading lines out of a generated image ----------
def extract_lines(gen, blot_crop=None, keep_near=0.35):
    """Thin dark strokes of a generated image (black-hat: what is darker than its surroundings, and thin).
    With blot_crop, strokes far from the blot are dropped, so the hint stays about this blot."""
    g = np.asarray(gen.convert("L"), np.float32) / 255.0; n = g.shape[0]
    r = max(2, n // 90)
    bh = ndi.grey_closing(g, size=(2 * r + 1, 2 * r + 1)) - g
    m = bh > 0.18
    m = ndi.binary_opening(m, iterations=1) if m.sum() > 50 else m
    lab, k = ndi.label(m); sizes = ndi.sum(m, lab, range(1, k + 1))
    m = np.isin(lab, 1 + np.flatnonzero(sizes >= max(12, 0.0002 * n * n)))
    if blot_crop is not None:
        b = np.asarray(Image.fromarray((blot_crop > 0.12).astype(np.uint8) * 255).resize((n, n))) > 0
        near = ndi.binary_dilation(b, iterations=int(keep_near * n / 2)) if b.any() else np.ones_like(b)
        m &= near
    return m.astype(np.float32)


# ---------- retrieval baseline ----------
def silhouette(ink, size=64):
    m = ink > 0.3
    if not m.any(): return np.zeros((size, size), bool)
    r = max(2, int(0.03 * max(m.shape)))
    s = ndi.binary_fill_holes(ndi.binary_closing(np.pad(m, r + 2), iterations=r))[r + 2:-r - 2, r + 2:-r - 2]
    ys, xs = np.nonzero(s); s = s[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = s.shape; k = size / max(h, w)
    im = Image.fromarray(s.astype(np.uint8) * 255).resize((max(1, round(w * k)), max(1, round(h * k))))
    out = np.zeros((size, size), bool); a = np.asarray(im) > 127
    out[(size - a.shape[0]) // 2:(size - a.shape[0]) // 2 + a.shape[0], (size - a.shape[1]) // 2:(size - a.shape[1]) // 2 + a.shape[1]] = a
    return out


class MotifIndex:
    """The manual's motifs (the LoRA training images), indexed by silhouette."""
    def __init__(self, data_dir):
        self.items = []
        meta = [json.loads(l) for l in open(os.path.join(data_dir, "metadata.jsonl"), encoding="utf-8")]
        for m in meta:
            ink = 1 - np.asarray(Image.open(os.path.join(data_dir, m["file_name"])).convert("L"), np.float32) / 255.0
            ys, xs = np.nonzero(ink > 0.3)
            if len(ys) < 50: continue
            ink = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            self.items.append({"meta": m, "ink": ink, "sil": silhouette(ink)})

    def best(self, blot_mask, k=3, rng=None):
        s = silhouette(blot_mask.astype(np.float32)); scored = []
        for i, it in enumerate(self.items):
            for flip in (False, True):
                t = it["sil"][:, ::-1] if flip else it["sil"]
                iou = (s & t).sum() / max(1, (s | t).sum()); scored.append((iou, i, flip))
        scored.sort(reverse=True); top = scored[:k]
        pick = top[0] if rng is None else top[rng.integers(len(top))]
        return pick

    def render(self, pick, box, shape):
        """The chosen motif's lines, stretched into the blot's bounding box, as a mask the size of the paper."""
        iou, i, flip = pick; ink = self.items[i]["ink"]; ink = ink[:, ::-1] if flip else ink
        H, W = shape; x0, y0, x1, y1 = box; w, h = max(1, x1 - x0), max(1, y1 - y0)
        im = Image.fromarray((np.clip(ink, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
        m = np.zeros(shape, np.float32); a = np.asarray(im, np.float32) / 255.0
        m[y0:y0 + h, x0:x0 + w] = a[:max(0, min(h, H - y0)), :max(0, min(w, W - x0))] if y0 >= 0 and x0 >= 0 else 0
        return (m > 0.35).astype(np.float32)


# ---------- the charcoal layer ----------
def place(mask_crop, crop_box, shape):
    """A line mask computed on a square crop, put back on the paper."""
    H, W = shape; X0, Y0, X1, Y1 = crop_box; s = X1 - X0
    m = np.asarray(Image.fromarray((mask_crop * 255).astype(np.uint8)).resize((s, s), Image.BILINEAR), np.float32) / 255.0
    out = np.zeros(shape, np.float32)
    sx0, sy0, sx1, sy1 = max(0, X0), max(0, Y0), min(W, X1), min(H, Y1)
    out[sy0:sy1, sx0:sx1] = m[sy0 - Y0:sy1 - Y0, sx0 - X0:sx1 - X0]
    return out


def charcoal_png(mask, strength=0.62):
    """Transparent PNG: lines in willow-charcoal grey, slightly soft, never as dark as ink."""
    a = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    a = np.asarray(a, np.float32) / 255.0 * strength
    rgba = np.zeros(mask.shape + (4,), np.uint8); rgba[..., :3] = CHARCOAL; rgba[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def preview(paper_img, layers, titles=None):
    """The paper with each charcoal layer over it, side by side."""
    tiles = []
    for L in layers:
        t = paper_img.convert("RGBA").copy(); t.alpha_composite(L); tiles.append(t.convert("RGB"))
    W, H = tiles[0].size; out = Image.new("RGB", (W * len(tiles) + 10 * (len(tiles) - 1), H), "white")
    for i, t in enumerate(tiles): out.paste(t, (i * (W + 10), 0))
    return out
