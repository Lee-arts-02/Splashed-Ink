#!/usr/bin/env python3
"""Download the web-size images of the works in data/curated.json into corpus/ (CC0 at the Cleveland Museum of Art).

    python tools/fetch_corpus.py

The images are kept on the separate `corpus` branch, not on main, so the published site stays small. They are there so the
works can be looked at while annotating motifs (data/motifs-annotations.json).
"""
import json, sys, time
from pathlib import Path
import io
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "splashed-ink-corpus (https://github.com/Lee-arts-02/Splashed-Ink)"}
out = ROOT / "corpus"; out.mkdir(exist_ok=True)
index = []
for w in json.loads((ROOT / "data/curated.json").read_text())["works"]:
    a = w["accession"]
    try:
        o = requests.get(f"https://openaccess-api.clevelandart.org/api/artworks/{a}", headers=UA, timeout=40).json()["data"]
    except Exception as e:
        print("fail", a, e); continue
    im = o.get("images") or {}
    u = (im.get("print") or {}).get("url") or (im.get("web") or {}).get("url")      # print size: handscrolls are unreadable at web size
    if o.get("share_license_status") != "CC0" or not u:
        print("skip", a); continue
    r = requests.get(u, headers=UA, timeout=120)
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    k = min(1.0, (6e6 / (img.width * img.height)) ** 0.5)                           # at most about 6 megapixels
    if k < 1: img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
    f = out / (a + ".jpg"); img.save(f, quality=88)
    index.append({"accession": a, "file": f.name, "title": o.get("title"), "artist": "; ".join(c.get("description", "") for c in o.get("creators") or []),
                  "url": o.get("url"), "image": u, "license": "CC0", "size": [img.width, img.height]})
    print(a, img.size); time.sleep(0.3)
(out / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False))
(out / "README.md").write_text("# Corpus\n\nWeb-size images of the works in `data/curated.json`, from the Cleveland Museum of Art's Open Access collection (CC0). Kept on this branch only, for annotating motifs.\n")
sys.exit(0 if index else 1)
