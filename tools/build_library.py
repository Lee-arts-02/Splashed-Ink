#!/usr/bin/env python3
"""Build a lobe library (splashed-ink-lobes/v1) from public-domain ink paintings.

    pip install playwright requests && python -m playwright install chromium
    python tools/build_library.py --out data/lobes-v1.json

It looks up xieyi painters in two CC0 open-access collections (the Cleveland Museum of Art and The Met), keeps ink
paintings marked public domain, downloads their web-size images to a temporary folder, and reads each one with
Machine Copy itself (apps/machine-copy) in a headless browser, so the library is built exactly as the app builds it.
Images are not kept; the library holds only lobe shapes, line positions and each painting's title, artist and source.

A browser cannot do this on its own: the museums' image servers do not let other web pages read their pixels.
The repository's "Build lobe library" workflow runs this script on GitHub's servers.
"""
import argparse, base64, json, re, sys, tempfile, time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTISTS = ["Bada Shanren", "Xu Wei", "Shitao", "Chen Chun", "Li Shan", "Li Fangying", "Huang Shen", "Gao Fenghan", "Gao Qipei",
           "Xugu", "Ren Yi", "Wu Changshuo", "Zhao Zhiqian", "Shen Zhou", "Zhu Da", "Jin Nong", "Luo Pin", "Wang Mian", "Mu Qi", "Liang Kai"]
UA = {"User-Agent": "splashed-ink-library-builder (https://github.com/Lee-arts-02/Splashed-Ink)"}
FLAGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


def get_json(url, tries=3):
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=40)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(1.5 * (k + 1))
    return None


def key_of(name):
    return re.compile(re.escape(name.split(" ")[0]), re.I)


def cleveland(name, per, log):
    j = get_json("https://openaccess-api.clevelandart.org/api/artworks/?" + requests.compat.urlencode(
        {"q": name, "cc0": 1, "has_image": 1, "type": "Painting", "limit": 60}))
    out = []
    for o in (j or {}).get("data", []):
        who = "; ".join(c.get("description", "") for c in o.get("creators") or [])
        if not key_of(name).search(who) or not re.search("ink", o.get("technique") or "", re.I):
            continue
        u = ((o.get("images") or {}).get("web") or {}).get("url")
        if u:
            out.append((u, {"title": o.get("title"), "artist": who, "date": o.get("creation_date") or "", "source": "Cleveland Museum of Art",
                            "url": o.get("url") or "", "image": u, "license": "CC0 (CMA Open Access)"}))
        if len(out) >= per:
            break
    log.append(f"Cleveland {name}: {len(out)}")
    return out


def met(name, per, log):
    MET = "https://collectionapi.metmuseum.org/public/collection/v1/"
    j = get_json(MET + "search?" + requests.compat.urlencode({"hasImages": "true", "q": name}))
    out, objs = [], 0
    for oid in ((j or {}).get("objectIDs") or [])[:60]:
        if objs >= per:
            break
        o = get_json(f"{MET}objects/{oid}")
        time.sleep(0.05)
        if not o or not o.get("isPublicDomain") or not re.search("ink", o.get("medium") or "", re.I):
            continue
        if not re.search("paint|album|scroll", (o.get("classification") or "") + " " + (o.get("objectName") or ""), re.I):
            continue
        if not key_of(name).search(o.get("artistDisplayName") or ""):
            continue
        imgs = [o.get("primaryImageSmall")] + [u.replace("/original/", "/web-large/") for u in o.get("additionalImages") or []]
        imgs = [u for u in imgs if u][:12]
        for k, u in enumerate(imgs):
            out.append((u, {"title": (o.get("title") or "") + (f" (image {k + 1})" if len(imgs) > 1 else ""), "artist": o.get("artistDisplayName") or "",
                            "date": o.get("objectDate") or "", "source": "The Metropolitan Museum of Art", "url": o.get("objectURL") or "",
                            "image": u, "license": "CC0 (The Met Open Access)"}))
        objs += 1
    log.append(f"Met {name}: {objs} works, {len(out)} images")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data/lobes-v1.json"))
    ap.add_argument("--per", type=int, default=10, help="works per painter per museum")
    ap.add_argument("--short", type=int, default=240, help="analysis resolution (short side), as Machine Copy's Detail menu")
    ap.add_argument("--artists", default="|".join(ARTISTS))
    a = ap.parse_args()

    log, items, seen = [], [], set()
    for name in a.artists.split("|"):
        for u, m in cleveland(name, a.per, log) + met(name, a.per, log):
            if u not in seen:
                seen.add(u)
                items.append((u, m))
    print("\n".join(log), flush=True)
    print(f"{len(items)} images to read", flush=True)

    tmp = Path(tempfile.mkdtemp())
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=FLAGS)
        page = browser.new_page(viewport={"width": 1000, "height": 900})
        page.set_default_timeout(120000)
        page.goto((ROOT / "apps/machine-copy/index.html").as_uri() + f"?sim={a.short}")
        page.wait_for_timeout(800)
        ok = 0
        for n, (u, m) in enumerate(items):
            try:
                r = requests.get(u, headers=UA, timeout=60)
                if r.status_code != 200 or len(r.content) < 2000:
                    print(f"skip {u}: HTTP {r.status_code}", flush=True)
                    continue
                mime = "image/png" if u.lower().endswith(".png") else "image/jpeg"
                data = f"data:{mime};base64," + base64.b64encode(r.content).decode()
                lobes = page.evaluate("([d,m])=>window.__mc.libAdd(d,m)", [data, m])
                ok += 1
                print(f"{n + 1}/{len(items)} {m['artist']}: {m['title']} -> {lobes} lobes", flush=True)
            except Exception as e:
                print(f"fail {u}: {e}", flush=True)
            time.sleep(0.2)
        lib = json.loads(page.evaluate("window.__mc.libraryJson()"))
        browser.close()

    lib["note"] = ("Built by tools/build_library.py from public-domain (CC0) ink paintings in the open-access collections of the Cleveland Museum "
                   "of Art and The Metropolitan Museum of Art. No images are included: only lobe shapes, line positions, and each work's title, artist and source.")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(lib, ensure_ascii=False, separators=(",", ":")))
    lines = sum(len(l["lines"]) for l in lib["lobes"])
    print(f"read {ok} images: {len(lib['paintings'])} paintings, {len(lib['lobes'])} lobes, {lines} lines -> {a.out}")
    src = Path(a.out).with_name("lobes-v1-sources.md")
    rows = ["# Paintings in lobes-v1.json", "", "All public domain (CC0) at their source. The library holds no images.", "",
            "| Painting | Artist | Date | Source | Lobes | Lines |", "|---|---|---|---|---|---|"]
    for p in lib["paintings"]:
        rows.append(f"| [{p.get('title','').replace('|','/')}]({p.get('url','')}) | {p.get('artist','').replace('|','/')} | {p.get('date','')} | {p.get('source','')} | {p.get('lobes',0)} | {p.get('lines',0)} |")
    src.write_text("\n".join(rows) + "\n")
    return 0 if lib["lobes"] else 1


if __name__ == "__main__":
    sys.exit(main())
