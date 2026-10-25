#!/usr/bin/env python3
"""Turn the hand-traced plates (data/manual-traced.json) into motif templates for the Reader (splashed-ink-motifs/v1).

    python tools/build_traced.py

Each template's strokes are put in its body frame: u along the long axis from -1 at the head (or base) to 1 at the tail
(or tip), v across it in half-widths. The order is the manual's drawing order and is kept.
"""
import json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PAGE = {"1125013": (1400, 1120)}           # pixel size of the fetched page spreads, so the page fractions have the right aspect

def main():
    d = json.loads((ROOT / "data/manual-traced.json").read_text()); out = []
    for t in d["templates"]:
        src = d["sources"][t["src"]]; IW, IH = src["size"]
        if t["coords"] == "frac": P = lambda x, y: (x * IW, y * IH)
        else:
            (rx0, ry0, rx1, ry1), (vw, vh) = t["region"], t["view"]
            P = lambda x, y, rx0=rx0, ry0=ry0, rx1=rx1, ry1=ry1, vw=vw, vh=vh: ((rx0 + x / vw * (rx1 - rx0)) * IW, (ry0 + y / vh * (ry1 - ry0)) * IH)
        (hx, hy), (tx, ty) = P(*t["head"]), P(*t["tail"])
        L = math.hypot(tx - hx, ty - hy); eu = ((tx - hx) / L, (ty - hy) / L); ev = (-eu[1], eu[0]); cx, cy = (hx + tx) / 2, (hy + ty) / 2
        Lh, hw = L / 2, t["hw"] * L
        lines, parts = [], []
        for s in t["strokes"]:
            pts = []
            for x, y in s["pts"]:
                X, Y = P(x, y); dx, dy = X - cx, Y - cy
                pts.append([round((dx * eu[0] + dy * eu[1]) / Lh, 3), round((dx * ev[0] + dy * ev[1]) / hw, 3), round(s.get("w", 0.006 * L) / hw, 3)])
            lines.append(pts); parts.append(s["part"])
        el = math.log(Lh / hw); prof = [round(math.sqrt(max(0, 1 - ((k + 0.5) / 4 - 1) ** 2)) * hw / Lh, 3) for k in range(8)]
        out.append({"label": t["label"], "zh": t["zh"], "note": t.get("pose", ""), "kind": "manual", "f": [round(el, 3)] + prof + prof + [0.5, -1.0],
                    "blotShare": 0, "lines": lines, "parts": parts, "dots": [], "sketch": t.get("sketch", 3),
                    "painting": {"title": src["title"] + (f", page {t['page']}" if "page" in t else ""), "artist": src.get("artist", "Mustard Seed Garden Manual (Wang Gai and others)"), "url": src["url"], "license": src["license"],
                                 "why": "key strokes traced by hand, in drawing order"}})
    (ROOT / "data/motifs-v1.json").write_text(json.dumps({"format": "splashed-ink-motifs/v1",
        "note": "Key strokes traced by hand from the Mustard Seed Garden Manual (public domain), in each motif's body frame, in the manual's drawing order.",
        "motifs": out}, ensure_ascii=False, separators=(",", ":")))
    print(len(out), "templates")

if __name__ == "__main__":
    main()
