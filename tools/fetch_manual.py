#!/usr/bin/env python3
"""Fetch pages of the Mustard Seed Garden Manual (Kaishien gaden, the 1935 Japanese edition in the National Diet Library's
digital collections, marked public domain) over IIIF, onto the `manual` branch, for finding its step-by-step drawing plates.

    python tools/fetch_manual.py --survey                  # every volume's title and page count, plus a small thumbnail sheet per volume
    python tools/fetch_manual.py --pages 1125020:12-40     # chosen pages at reading size
"""
import argparse, io, json, sys, time
from pathlib import Path
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "manual"; OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "splashed-ink-manual (https://github.com/Lee-arts-02/Splashed-Ink)"}

def manifest(pid):
    r = requests.get(f"https://dl.ndl.go.jp/api/iiif/{pid}/manifest.json", headers=UA, timeout=60)
    return r.json() if r.status_code == 200 else None

def canvases(m):
    if "items" in m: return [(c.get("label"), c["items"][0]["items"][0]["body"]["service"][0].get("id") or c["items"][0]["items"][0]["body"]["service"][0].get("@id")) for c in m["items"]]
    out = []
    for c in m["sequences"][0]["canvases"]:
        svc = c["images"][0]["resource"]["service"]; out.append((c.get("label"), svc.get("@id") or svc.get("id")))
    return out

def label(m):
    l = m.get("label");
    if isinstance(l, dict): l = " ".join(sum(l.values(), []))
    return str(l)

def get(svc, width):
    r = requests.get(f"{svc}/full/{width},/0/default.jpg", headers=UA, timeout=90)
    return Image.open(io.BytesIO(r.content)).convert("RGB")

ap = argparse.ArgumentParser(); ap.add_argument("--survey", action="store_true"); ap.add_argument("--pids", default="1125010-1125030"); ap.add_argument("--pages", default="")
a = ap.parse_args()
if a.survey:
    lo, hi = map(int, a.pids.split("-")); vols = []
    for pid in range(lo, hi + 1):
        m = manifest(pid)
        if not m: print(pid, "none"); continue
        cs = canvases(m); vols.append({"pid": pid, "label": label(m), "pages": len(cs)}); print(pid, label(m), len(cs), flush=True)
        if "芥子" not in label(m) and "Kaishien" not in label(m): continue
        thumbs = []
        for i, (_, svc) in enumerate(cs):
            try: im = get(svc, 160); thumbs.append(im)
            except Exception as e: print("thumb fail", pid, i, e)
            time.sleep(0.15)
        cols = 12; w, h = 170, 240; sheet = Image.new("RGB", (cols * w, ((len(thumbs) + cols - 1) // cols) * h), "white")
        from PIL import ImageDraw
        d = ImageDraw.Draw(sheet)
        for i, im in enumerate(thumbs):
            im.thumbnail((160, 220)); x, y = (i % cols) * w, (i // cols) * h; sheet.paste(im, (x + 5, y + 5)); d.text((x + 5, y + 226), str(i + 1), fill=(200, 0, 0))
        sheet.save(OUT / f"sheet-{pid}.jpg", quality=80)
    (OUT / "volumes.json").write_text(json.dumps(vols, ensure_ascii=False, indent=1))
for spec in filter(None, a.pages.split(",")):
    pid, rng = spec.split(":"); s, e = map(int, rng.split("-")); cs = canvases(manifest(int(pid)))
    for i in range(s, e + 1):
        im = get(cs[i - 1][1], 1400); im.save(OUT / f"{pid}-{i:03d}.jpg", quality=85); print(pid, i, im.size, flush=True); time.sleep(0.3)
