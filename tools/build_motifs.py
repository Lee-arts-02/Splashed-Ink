#!/usr/bin/env python3
"""Build the motif library (splashed-ink-motifs/v1) from the hand-boxed motifs in data/motifs-annotations.json.

    pip install playwright pillow && python -m playwright install chromium
    python tools/build_motifs.py --corpus path/to/corpus      # the images from the `corpus` branch (tools/fetch_corpus.py)

Each motif is cut out of its painting with a margin, read by Machine Copy in a headless browser (apps/machine-copy,
motifRecord), and stored in the frame of its blot: the cleaned lines and dots a painter drew around one blot of ink.
"""
import argparse, base64, io, json, sys
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", default=str(ROOT / "data/motifs-v1.json"))
    ap.add_argument("--short", type=int, default=260)
    a = ap.parse_args()
    corpus = Path(a.corpus)
    index = {w["accession"]: w for w in json.loads((corpus / "index.json").read_text())}
    curated = {w["accession"]: w for w in json.loads((ROOT / "data/curated.json").read_text())["works"]}
    ann = json.loads((ROOT / "data/motifs-annotations.json").read_text())["motifs"]
    out = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=FLAGS); page = b.new_page(viewport={"width": 900, "height": 900}); page.set_default_timeout(120000)
        page.goto((ROOT / "apps/machine-copy/index.html").as_uri() + f"?sim={a.short}"); page.wait_for_timeout(600)
        for m in ann:
            w = index.get(m["accession"])
            if not w: print("missing", m["accession"]); continue
            im = Image.open(corpus / w["file"]).convert("RGB"); W, H = im.size
            x0, y0, x1, y1 = m["box"]; mx, my = 0.08 * (x1 - x0), 0.08 * (y1 - y0)
            cx0, cy0, cx1, cy1 = max(0, x0 - mx), max(0, y0 - my), min(1, x1 + mx), min(1, y1 + my)
            crop = im.crop((round(cx0 * W), round(cy0 * H), round(cx1 * W), round(cy1 * H)))
            buf = io.BytesIO(); crop.save(buf, "JPEG", quality=92)
            inner = [(x0 - cx0) / (cx1 - cx0), (y0 - cy0) / (cy1 - cy0), (x1 - cx0) / (cx1 - cx0), (y1 - cy0) / (cy1 - cy0)]
            rec = page.evaluate("([d,i])=>window.__mc.motif(d,i)", ["data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), inner])
            if not rec: print("no blot", m["label"]); continue
            out.append({"label": m["label"], "zh": m["zh"], "note": m["note"],
                        "painting": {"accession": m["accession"], "title": w["title"], "artist": w["artist"], "url": w["url"], "license": "CC0 (CMA Open Access)",
                                     "why": curated.get(m["accession"], {}).get("why", "")}, **rec})
            print(f"{m['label']:28s} {rec['kind']:5s} lines {len(rec['lines']):3d} dots {len(rec["dots"]):3d}", flush=True)
        b.close()
    doc = {"format": "splashed-ink-motifs/v1",
           "note": "Motifs boxed by hand in public-domain (CC0) paintings and read by Machine Copy. Each holds the lines and dots its painter drew, in the frame of its blot of ink (LobeKit). No images are included.",
           "lineColumns": ["u (along the blot's long axis, -1 fuller end to 1 thinner end)", "v (across, in half-widths, positive toward the heavier side)", "width (in half-widths)"],
           "motifs": out}
    Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    print(len(out), "motifs ->", a.out)
    return 0 if out else 1

if __name__ == "__main__":
    sys.exit(main())
