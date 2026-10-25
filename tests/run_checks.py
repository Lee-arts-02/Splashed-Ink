#!/usr/bin/env python3
"""End-to-end checks for the two apps, run in a real browser.

    pip install playwright jsonschema
    playwright install chromium
    python tests/run_checks.py

What is checked
  1. Determinism: a scripted session (strokes, tilt, setting changes, undo, new sheet, two partner turns)
     is recorded, saved to JSON, and replayed. The two pictures must match pixel for pixel.
  2. Undo is exact: the picture after an undo equals the picture before the stroke.
  3. Each friction setting changes what it says it changes, and the brush behaves like a brush: slow strokes are heavier than fast
     ones, the pot is spent by distance and refills when the brush is lifted, and a partner can draw a line.
  4. A partner receives the person's words and strokes only when the settings allow it, and the built-in
     partners (Chance, Echo, Counterweight) answer without any backend.
  5. URL parameters set and lock the settings.
  6. Machine Copy extracts a plan from a synthetic image, paints it, and exports a file that passes the schema.
  7. Exported example files pass the schemas.

Pass --splashed or --machine-copy to run one half. The browser flags below use software rendering so that this also runs on a machine without a GPU. It is slow (minutes).
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
RUN_SI = "--machine-copy" not in sys.argv      # python tests/run_checks.py --splashed  or  --machine-copy  to run half
RUN_MC = "--splashed" not in sys.argv

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
  si.step(20); si.tool('brush'); si.pd('b1', 0.2, 0.8, 0.5); for (let i = 1; i <= 25; i++) { si.step(1); si.pm('b1', 0.2 + i * 0.02, 0.8 - Math.sin(i / 5) * 0.05, 0.5); } si.pu('b1'); si.step(10);
  si.knob('roles', 'free'); si.tool('line'); si.pd('l1', 0.25, 0.3, 0.5); for (let i = 1; i <= 15; i++) { si.step(1); si.pm('l1', 0.25 + i * 0.03, 0.3 + i * 0.01, 0.6); } si.pu('l1'); si.step(5); si.tool('pour');
  si.g(0.1, 0.7); si.step(40); si.g(0, 0);
  si.knob('ink', 'unlimited'); si.pot(0.45);
  si.pd('u3', 0.7, 0.5, 0.5); for (let i = 1; i <= 12; i++) { si.step(2); si.pm('u3', 0.7 - i * 0.02, 0.5 + i * 0.01, 0.5); } si.pu('u3');
  si.knob('drying', 'fast'); si.step(25); si.sheet(12345); si.step(5);
  si.pd('u4', 0.4, 0.4, 0.5); for (let i = 1; i <= 10; i++) { si.step(2); si.pm('u4', 0.4, 0.4 + i * 0.02, 0.5); } si.pu('u4'); si.step(10);
  si.pass([{type:'pour',x:0.6,y:0.3,seconds:0.5,path:[[0.7,0.35]],ink:0.8},{type:'stroke',path:[[0.2,0.2],[0.5,0.3],[0.8,0.2]],seconds:0.8},{type:'outline',path:[[0.3,0.6],[0.5,0.62],[0.6,0.7]],seconds:0.5,press:0.7},{type:'tilt',dx:0.3,dy:1,seconds:0.5},{type:'wait',seconds:0.5}], 'a few words');
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
BRUSH = """
() => { const si = window.__si, r = {};
  const line = (perTick, ink, rest) => { si.start(); si.knob('ink', ink || 'unlimited'); if (!ink) si.pot(1); si.tool('brush');
    si.pd('a', 0.15, 0.5, 0.5); const n = Math.round(0.7 / perTick); for (let i = 1; i <= n; i++) { si.step(1); si.pm('a', 0.15 + i * perTick, 0.5, 0.5); }
    const C = si.E.C; si.pu('a'); si.step(rest || 40); return { C, D: si.density(), C2: si.E.C }; };
  const area = d => d.filter(v => v > 76).length, total = d => d.reduce((a, b) => a + b, 0);
  const slow = line(0.004), fast = line(0.035);
  r.areaSlow = area(slow.D); r.areaFast = area(fast.D); r.inkSlow = total(slow.D); r.inkFast = total(fast.D);
  r.potNormal = line(0.012, 'normal').C; r.potScarce = line(0.012, 'scarce').C; r.potUnlimited = line(0.012, 'unlimited').C;
  const rest = line(0.012, 'normal', 150); r.refilled = rest.C2 - rest.C;
  // a partner draws a line with the same brush
  si.start(); si.pass([{ type: 'stroke', path: [[0.2, 0.5], [0.8, 0.5]], seconds: 1 }]); let g = 0; while (si.E.actor && g++ < 400) si.step(1); si.step(40);
  const D = si.density(), [w, h] = si.session.device.sim, band = (y0, y1) => { let t = 0, c = 0; for (let y = Math.round(y0 * h); y < Math.round(y1 * h); y++) for (let x = Math.round(0.3 * w); x < Math.round(0.7 * w); x++) { t += D[y * w + x]; c++; } return t / c; };
  r.partnerLine = band(0.46, 0.54); r.partnerElsewhere = band(0.1, 0.2);
  return r; }
"""
PARTNER = """
async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms)), si = window.__si, out = {};
  document.getElementById('start').click(); await sleep(600);
  si.pd('a', 0.3, 0.3, 0.5); await sleep(150); si.pm('a', 0.4, 0.35, 0.5); await sleep(150); si.pm('a', 0.5, 0.4, 0.5); await sleep(150); si.pu('a');
  await sleep(300); si.pd('b', 0.6, 0.6, 0.5); await sleep(200); si.pm('b', 0.6, 0.7, 0.5); await sleep(200); si.pu('b');
  document.getElementById('words').value = 'make room for the cloud';
  const sel = document.getElementById('partnerSel'); sel.value = 'test'; sel.dispatchEvent(new Event('change'));
  document.getElementById('pass').click();
  for (let i = 0; i < 60 && !window.__ctx; i++) await sleep(200);
  const c = window.__ctx || {}, p = c.prompt || '';
  out.hasWords = p.includes('make room for the cloud'); out.hasStrokes = p.includes('recent strokes'); out.strokes = (c.strokes || []).length;
  for (let i = 0; i < 300 && si.E.aiTurn; i++) await sleep(200);
  out.finished = !si.E.aiTurn; return out;
}
"""
BUILTIN = """
async (name) => {
  const sleep = ms => new Promise(r => setTimeout(r, ms)), si = window.__si, out = {};
  document.getElementById('start').click(); await sleep(500); si.knob('sees', 'paper+strokes'); if (window.__brush) si.tool('brush');
  si.pd('a', 0.2, 0.3, 0.5); await sleep(120); si.pm('a', 0.3, 0.35, 0.5); await sleep(120); si.pm('a', 0.4, 0.45, 0.5); await sleep(120); si.pu('a'); await sleep(300);
  const sel = document.getElementById('partnerSel'); out.options = [...sel.options].map(o => o.value);
  sel.value = name; sel.dispatchEvent(new Event('change')); document.getElementById('pass').click();
  for (let i = 0; i < 80 && !si.session.events.some(e => e.e === 'pg'); i++) await sleep(150);
  const pg = si.session.events.find(e => e.e === 'pg'); out.gestures = pg ? pg.gestures : null;
  for (let i = 0; i < 500 && si.E.aiTurn; i++) await sleep(150);   // software rendering is slow; the partner's gestures last a few seconds of simulated time
  out.finished = !si.E.aiTurn; return out;
}
"""
ROLES = """
() => { const si = window.__si, out = {};
  si.start(); out.defaultRole = si.E.settings.roles; si.tool('line'); out.triedLine = si.E.tool; si.tool('brush'); out.brushOK = si.E.tool;
  si.knob('roles', 'partner-splash'); out.afterSwitch = si.E.tool;
  si.knob('roles', 'free'); si.tool('pour'); si.pd('w', 0.5, 0.5, 0.5); si.step(60); si.pu('w'); si.step(10);
  const wet = () => si.paper().wet.filter(v => v > 0.05).length; out.wetAfter = wet(); si.step(900); out.wetLater = wet();
  const area = tool => { si.start(); si.knob('roles', 'free'); si.knob('ink', 'unlimited'); si.pot(1); si.tool(tool); si.pd('s', 0.2, 0.5, 0.5);
    for (let i = 1; i <= 30; i++) { si.step(1); si.pm('s', 0.2 + i * 0.02, 0.5, 0.5); } si.pu('s'); si.step(120); return si.density().filter(v => v > 38).length; };
  out.brushArea = area('brush'); out.lineArea = area('line'); return out; }
"""
SPEC_PAINT = """
() => { const c = document.createElement('canvas'); c.width = 300; c.height = 400; const x = c.getContext('2d');
  x.fillStyle = '#e6dcc4'; x.fillRect(0, 0, 300, 400); x.fillStyle = '#25262a'; x.beginPath(); x.ellipse(150, 170, 90, 50, 0.3, 0, 7); x.fill();
  x.strokeStyle = '#25262a'; x.lineWidth = 6; x.beginPath(); x.moveTo(40, 320); x.lineTo(150, 340); x.lineTo(260, 310); x.stroke();
  return c.toDataURL('image/png').split(',')[1]; }
"""

with sync_playwright() as pw:
    browser = pw.chromium.launch(args=FLAGS)

    if RUN_SI:
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
        b = page.evaluate(BRUSH)
        check("a slow brush stroke lays down more ink than a fast one", b["areaSlow"] > b["areaFast"] and b["inkSlow"] > b["inkFast"], f"area {b['areaSlow']} vs {b['areaFast']}")
        check("the brush spends the pot by distance, and more when ink is scarce", 0.6 < b["potNormal"] < 0.8 and b["potScarce"] < b["potNormal"] and b["potUnlimited"] == 1, f"{b['potNormal']:.2f} / {b['potScarce']:.2f} / {b['potUnlimited']:.2f}")
        check("a lifted brush is dipped again", b["refilled"] > 0.2, f"+{b['refilled']:.2f}")
        check("a partner's brush stroke leaves ink along its path", b["partnerLine"] > 8 * max(b["partnerElsewhere"], 0.5), f"{b['partnerLine']:.1f} on the line, {b['partnerElsewhere']:.1f} elsewhere")
        check("no script errors in the first page", not errors, "; ".join(errors[:2]))
        page.close()

        # --- 4-5. partner context and URL parameters
        ctx = browser.new_context(viewport={"width": 200, "height": 300})
        ctx.add_init_script("window.InkPartners={test:{label:'Test',async turn(c){window.__ctx=c;return {gestures:[{type:'pour',x:0.5,y:0.5,seconds:0.4,path:[]}]};}}};")
        p2 = ctx.new_page(); p2.set_default_timeout(280000)
        p2.goto(SI + "?words=on&sees=paper%2Bstrokes&roles=free"); p2.wait_for_timeout(600)
        r = p2.evaluate(PARTNER)
        check("the partner is told the person's words and strokes when allowed", r["hasWords"] and r["hasStrokes"] and r["strokes"] == 2 and r["finished"], str(r))
        p3 = ctx.new_page(); p3.goto(SI + "?roles=free"); p3.wait_for_timeout(500)
        p3.evaluate("document.getElementById('words').value='secret'"); p3.evaluate("document.getElementById('start').click()"); p3.wait_for_timeout(400)
        p3.evaluate("window.__si.pd('a',0.3,0.3,0.5); window.__si.pu('a')"); p3.evaluate("(()=>{const s=document.getElementById('partnerSel'); s.value='test'; s.dispatchEvent(new Event('change'));})()"); p3.evaluate("document.getElementById('pass').click()")
        for _ in range(50):
            if p3.evaluate("!!window.__ctx"): break
            p3.wait_for_timeout(200)
        c = p3.evaluate("({prompt: window.__ctx.prompt, strokes: window.__ctx.strokes, words: window.__ctx.words})")
        check("by default the partner sees only the paper", c["strokes"] is None and c["words"] == "" and "secret" not in c["prompt"])
        p4 = ctx.new_page(); p4.goto(SI + "?lock=1&preset=seamless"); p4.wait_for_timeout(500)
        p4.evaluate("document.getElementById('start').click()"); p4.wait_for_timeout(300)
        locked = p4.evaluate("({hidden: document.getElementById('fricBtn').hidden, s: window.__si.E.settings})")
        check("URL parameters set and lock the settings", locked["hidden"] and locked["s"]["undo"] == "unlimited" and locked["s"]["drying"] == "instant")

        # --- built-in partners, no backend
        for name in ("echo", "counterweight", "chance"):
            bp = browser.new_page(viewport={"width": 200, "height": 300}); bp.set_default_timeout(120000); bp.goto(SI + "?roles=free"); bp.wait_for_timeout(600)
            r = bp.evaluate(BUILTIN, name); g = r["gestures"] or []
            ok = r["finished"] and len(g) > 0 and {"echo", "counterweight", "chance"} <= set(r["options"])
            if name == "echo":
                ok = ok and abs(g[0]["x"] - 0.8) < 0.01 and abs(g[0]["path"][-1][0] - 0.6) < 0.01          # the stroke, mirrored left to right
            if name == "counterweight":
                ok = ok and g[0]["x"] > 0.5 and any(x["type"] == "tilt" for x in g)                       # opposite the ink, then tilting toward it
            check(f"the built-in partner '{name}' answers with no backend", ok, json.dumps(g)[:90])
            bp.close()
        bp = browser.new_page(viewport={"width": 200, "height": 300}); bp.set_default_timeout(120000)
        bp.add_init_script("window.__brush = true;"); bp.goto(SI + "?roles=free"); bp.wait_for_timeout(600)
        r = bp.evaluate(BUILTIN, "echo"); g = r["gestures"] or []
        check("Echo answers a brush stroke with a brush stroke", r["finished"] and g and g[0]["type"] == "stroke" and abs(g[0]["path"][0][0] - 0.8) < 0.01, json.dumps(g)[:90])
        bp.close()

        # --- roles: one splashes, the other outlines
        rp = browser.new_page(viewport={"width": 240, "height": 360}); rp.set_default_timeout(200000); rp.goto(SI); rp.wait_for_timeout(600)
        t = rp.evaluate(ROLES)
        check("by default you splash and cannot outline", t["defaultRole"] == "you-splash" and t["triedLine"] == "pour" and t["brushOK"] == "brush", str(t))
        check("switching to 'partner splashes' gives you only the outlining brush", t["afterSwitch"] == "line", str(t))
        check("wet paper is visible to a partner and dries", t["wetAfter"] > 20 and t["wetLater"] < t["wetAfter"] * 0.2, f"{t['wetAfter']} wet cells, {t['wetLater']} later")
        check("a fine outline is narrower than a brush stroke", 0 < t["lineArea"] < 0.5 * t["brushArea"], f"{t['lineArea']} vs {t['brushArea']}")
        rp.close()
        rp = browser.new_page(viewport={"width": 240, "height": 360}); rp.set_default_timeout(200000); rp.goto(SI); rp.wait_for_timeout(600)
        r = rp.evaluate(BUILTIN, "reader"); g = r["gestures"] or []
        check("Reader answers a splash only with outlines", r["finished"] and len(g) >= 2 and all(x["type"] in ("outline", "wait") for x in g) and r["options"][0] == "reader", json.dumps(g)[:120])
        rp.close()
        rp = browser.new_page(viewport={"width": 240, "height": 360}); rp.set_default_timeout(200000); rp.goto(SI + "?roles=partner-splash"); rp.wait_for_timeout(600)
        r = rp.evaluate(BUILTIN, "splasher"); g = r["gestures"] or []
        check("Splasher pours and never outlines", r["finished"] and g and not any(x["type"] == "outline" for x in g) and r["options"][0] == "splasher", json.dumps(g)[:120])
        rp.close()

    if RUN_MC:
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
        sc = mc.evaluate("window.__mc.lastScore")
        check("a finished copy reports tone error and line recall separately",
              sc is not None and 0 <= sc["toneError"] <= 1 and sc["lineRecall"] is not None, json.dumps(sc)[:160])
        # the score must notice a missing line even when the broad tone is right
        cmp = mc.evaluate("""(()=>{ const w=120,h=90, A=new Array(w*h).fill(0);
          for(let y=20;y<70;y++) for(let x=20;x<60;x++) A[y*w+x]=0.5;              // a wash
          const B=A.slice(); for(let y=10;y<80;y++){ A[y*w+90]=0.9; A[y*w+91]=0.9; } // a thin line, only in the original
          return {same:window.__mc.scoreMaps(A,A,w,h), lost:window.__mc.scoreMaps(B,A,w,h)}; })()""")
        check("identical images score zero tone error and full line recall",
              cmp["same"]["toneError"] < 1e-6 and cmp["same"]["lineRecall"] == 1, json.dumps(cmp["same"])[:120])
        check("a missing line drops line recall while tone error stays small",
              cmp["lost"]["lineRecall"] < 0.2 and cmp["lost"]["toneError"] < 0.35, json.dumps(cmp["lost"])[:160])
        before = sc["toneError"]
        mc.evaluate("window.__mc.refine()")
        t0 = time.time()
        while time.time() - t0 < 240 and mc.evaluate("window.__mc.pump(15000)"):
            pass
        after = mc.evaluate("window.__mc.lastScore")["toneError"]
        check("Refine tone does not make the tone worse", after <= before + 0.01, f"{before:.3f} -> {after:.3f}")
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
