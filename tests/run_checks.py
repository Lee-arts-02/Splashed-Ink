#!/usr/bin/env python3
"""End-to-end checks for the two apps, run in a real browser.

    pip install playwright jsonschema
    playwright install chromium
    python tests/run_checks.py

What is checked
  1. Determinism: a scripted session (strokes, tilt, setting changes, undo, new sheet, two partner turns)
     is recorded, saved to JSON, and replayed. The two pictures must match pixel for pixel.
  2. Undo is exact: the picture after an undo equals the picture before the stroke.
  3. Each friction setting changes what it says it changes.
  4. A partner receives the person's words and strokes only when the settings allow it.
  5. URL parameters set and lock the settings.
  6. Machine Copy extracts a plan from a synthetic image, paints it, and exports a file that passes the schema.
  7. Exported example files pass the schemas.

The browser flags below use software rendering so that this also runs on a machine without a GPU. It is slow (minutes).
"""
import base64, json, math, sys, tempfile, time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("This needs Playwright: pip install playwright && playwright install chromium")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import validate  # noqa: E402

SI = (ROOT / "apps/splashed-ink/index.html").as_uri()
MC = (ROOT / "apps/machine-copy/index.html").as_uri()
FLAGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
failures = []

def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"   {detail}" if detail else ""), flush=True)
    if not ok:
        failures.append(name)

DETERMINISM = """
() => {
  const si = window.__si, out = {};
  si.start(); si.knob('undo', 'unlimited');
  si.pd('u1', 0.3, 0.3, 0.6); for (let i = 1; i <= 20; i++) { si.step(2); si.pm('u1', 0.3 + i * 0.02, 0.3 + Math.sin(i / 3) * 0.05, 0.6); } si.pu('u1');
  si.step(30);
  const before = si.density();
  si.pd('u2', 0.5, 0.6, 0.5); for (let i = 1; i <= 15; i++) { si.step(2); si.pm('u2', 0.5, 0.6 + i * 0.01, 0.5); } si.pu('u2');
  si.undo();
  const after = si.density();
  out.undoExact = before.every((v, i) => v === after[i]);
  si.step(20); si.g(0.1, 0.7); si.step(40); si.g(0, 0);
  si.knob('ink', 'unlimited'); si.pot(0.45);
  si.pd('u3', 0.7, 0.5, 0.5); for (let i = 1; i <= 12; i++) { si.step(2); si.pm('u3', 0.7 - i * 0.02, 0.5 + i * 0.01, 0.5); } si.pu('u3');
  si.knob('drying', 'fast'); si.step(25); si.sheet(12345); si.step(5);
  si.pd('u4', 0.4, 0.4, 0.5); for (let i = 1; i <= 10; i++) { si.step(2); si.pm('u4', 0.4, 0.4 + i * 0.02, 0.5); } si.pu('u4'); si.step(10);
  si.pass([{type:'pour',x:0.6,y:0.3,seconds:0.5,path:[[0.7,0.35]],ink:0.8},{type:'tilt',dx:0.3,dy:1,seconds:0.5},{type:'wait',seconds:0.5}], 'a few words');
  let g = 0; while (si.E.actor && g++ < 400) si.step(1);
  out.partnerFinished = !si.E.actor && !si.E.aiTurn;
  si.step(15); si.redo(); si.pass([{type:'pour',x:0.3,y:0.7,seconds:0.5,path:[]}]);
  g = 0; while (si.E.actor && g++ < 400) si.step(1);
  si.step(30);
  const live = si.density(), s = si.finish(), text = si.serialize(s);
  si.replayHeadless(JSON.parse(text));
  const replay = si.density();
  out.differing = live.filter((v, i) => v !== replay[i]).length; out.ink = live.filter(v => v > 20).length; out.text = text;
  return out;
}
"""
KNOBS = """
() => { const si = window.__si, r = {};
  const area = d => { si.start(); si.knob('drying', d); si.pd('a', 0.5, 0.4, 0.6); si.step(50); si.pu('a'); si.g(0, 0.7); si.step(80); si.g(0, 0); si.step(40); return si.density().filter(v => v > 38).length; };
  r.area = { slow: area('slow'), normal: area('normal'), fast: area('fast'), instant: area('instant') };
  const pot = k => { si.start(); if (k !== 'normal') si.knob('ink', k); si.pd('a', 0.5, 0.5, 0.6); si.step(120); const c = si.E.C; si.pu('a'); return c; };
  r.pot = { scarce: pot('scarce'), normal: pot('normal'), unlimited: pot('unlimited') };
  const depth = u => { si.start(); si.knob('undo', u); for (let i = 0; i < 4; i++) { si.pd('a', 0.3 + i * 0.1, 0.5, 0.5); si.step(5); si.pu('a'); si.step(3); } return si.snapDepth(); };
  r.depth = { none: depth('none'), one: depth('one'), unlimited: depth('unlimited') };
  return r; }
"""
PARTNER = """
async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms)), si = window.__si, out = {};
  document.getElementById('start').click(); await sleep(600);
  si.pd('a', 0.3, 0.3, 0.5); await sleep(150); si.pm('a', 0.4, 0.35, 0.5); await sleep(150); si.pm('a', 0.5, 0.4, 0.5); await sleep(150); si.pu('a');
  await sleep(300); si.pd('b', 0.6, 0.6, 0.5); await sleep(200); si.pm('b', 0.6, 0.7, 0.5); await sleep(200); si.pu('b');
  document.getElementById('words').value = 'make room for the cloud';
  document.getElementById('pass').click();
  for (let i = 0; i < 60 && !window.__ctx; i++) await sleep(200);
  const c = window.__ctx || {}, p = c.prompt || '';
  out.hasWords = p.includes('make room for the cloud'); out.hasStrokes = p.includes('recent strokes'); out.strokes = (c.strokes || []).length;
  for (let i = 0; i < 80 && si.E.aiTurn; i++) await sleep(200);
  out.finished = !si.E.aiTurn; return out;
}
"""
SPEC_PAINT = """
() => { const c = document.createElement('canvas'); c.width = 300; c.height = 400; const x = c.getContext('2d');
  x.fillStyle = '#e6dcc4'; x.fillRect(0, 0, 300, 400); x.fillStyle = '#25262a'; x.beginPath(); x.ellipse(150, 170, 90, 50, 0.3, 0, 7); x.fill();
  x.strokeStyle = '#25262a'; x.lineWidth = 6; x.beginPath(); x.moveTo(40, 320); x.lineTo(150, 340); x.lineTo(260, 310); x.stroke();
  return c.toDataURL('image/png').split(',')[1]; }
"""

with sync_playwright() as pw:
    browser = pw.chromium.launch(args=FLAGS)

    # --- 1-2. determinism and exact undo
    page = browser.new_page(viewport={"width": 200, "height": 300}); page.set_default_timeout(280000)
    errors = []; page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(SI); page.wait_for_timeout(800)
    r = page.evaluate(DETERMINISM)
    check("a recorded session replays to the identical picture", r["differing"] == 0 and r["ink"] > 100, f"{r['differing']} differing pixels, {r['ink']} ink pixels")
    check("undo restores the picture exactly", r["undoExact"])
    check("a partner's turn runs to the end", r["partnerFinished"])
    tmp = Path(tempfile.mkdtemp()) / "session.json"; tmp.write_text(r["text"])
    issues = validate.check(tmp)
    check("the exported session passes the schema", not issues, "; ".join(issues[:2]))

    # --- 3. friction settings
    k = page.evaluate(KNOBS)
    a = k["area"]
    check("the faster the paper dries, the less the ink runs", a["slow"] >= a["normal"] > a["fast"] > a["instant"], str(a))
    p = k["pot"]
    check("the ink pot empties by the chosen amount", p["scarce"] < p["normal"] < 1 and p["unlimited"] == 1, str({x: round(y, 2) for x, y in p.items()}))
    d = k["depth"]
    check("the undo stack holds none, one or many strokes", d == {"none": 0, "one": 1, "unlimited": 4}, str(d))
    check("no script errors in the first page", not errors, "; ".join(errors[:2]))
    page.close()

    # --- 4-5. partner context and URL parameters
    ctx = browser.new_context(viewport={"width": 200, "height": 300})
    ctx.add_init_script("window.InkPartners={test:{label:'Test',async turn(c){window.__ctx=c;return {gestures:[{type:'pour',x:0.5,y:0.5,seconds:0.4,path:[]}]};}}};")
    p2 = ctx.new_page(); p2.set_default_timeout(280000)
    p2.goto(SI + "?words=on&sees=paper%2Bstrokes"); p2.wait_for_timeout(600)
    r = p2.evaluate(PARTNER)
    check("the partner is told the person's words and strokes when allowed", r["hasWords"] and r["hasStrokes"] and r["strokes"] == 2 and r["finished"], str(r))
    p3 = ctx.new_page(); p3.goto(SI); p3.wait_for_timeout(500)
    p3.evaluate("document.getElementById('words').value='secret'"); p3.evaluate("document.getElementById('start').click()"); p3.wait_for_timeout(400)
    p3.evaluate("window.__si.pd('a',0.3,0.3,0.5); window.__si.pu('a')"); p3.evaluate("document.getElementById('pass').click()")
    for _ in range(50):
        if p3.evaluate("!!window.__ctx"): break
        p3.wait_for_timeout(200)
    c = p3.evaluate("({prompt: window.__ctx.prompt, strokes: window.__ctx.strokes, words: window.__ctx.words})")
    check("by default the partner sees only the paper", c["strokes"] is None and c["words"] == "" and "secret" not in c["prompt"])
    p4 = ctx.new_page(); p4.goto(SI + "?lock=1&preset=seamless"); p4.wait_for_timeout(500)
    p4.evaluate("document.getElementById('start').click()"); p4.wait_for_timeout(300)
    locked = p4.evaluate("({hidden: document.getElementById('fricBtn').hidden, s: window.__si.E.settings})")
    check("URL parameters set and lock the settings", locked["hidden"] and locked["s"]["undo"] == "unlimited" and locked["s"]["drying"] == "instant")

    # --- 6. Machine Copy
    mc = browser.new_page(viewport={"width": 1000, "height": 800}); mc.set_default_timeout(280000)
    mc.goto(MC + "?sim=60&spf=400"); mc.wait_for_timeout(500)
    png = base64.b64decode(mc.evaluate(SPEC_PAINT))
    mc.set_input_files("#file", files=[{"name": "synthetic.png", "mimeType": "image/png", "buffer": png}]); mc.wait_for_timeout(1200)
    plan = mc.evaluate("(()=>{const p=window.__mc.plan; return {ws:p.washStrokes.length, w:p.washes.length, s:p.strokes.length}})()")
    check("Machine Copy finds ink to copy in a synthetic image", plan["ws"] + plan["w"] > 0 and plan["s"] > 0, str(plan))
    mc.evaluate("document.getElementById('run').click()")
    t0 = time.time()
    while time.time() - t0 < 240 and mc.evaluate("window.__mc.pump(15000)"):
        pass
    data = mc.evaluate("window.__mc.exportJson()")
    tmp2 = Path(tempfile.mkdtemp()) / "plan.json"; tmp2.write_text(data)
    issues = validate.check(tmp2)
    check("the exported plan passes the schema", not issues, "; ".join(issues[:2]))
    browser.close()

# --- 7. shipped examples
for f in sorted((ROOT / "examples").glob("*.json")):
    issues = validate.check(f)
    check(f"examples/{f.name} passes its schema", not issues, "; ".join(issues[:2]))

print()
print("All checks passed." if not failures else f"{len(failures)} check(s) failed: " + ", ".join(failures))
sys.exit(1 if failures else 0)
