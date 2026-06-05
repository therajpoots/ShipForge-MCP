"""
MCP-ShipForge Control Dashboard — Enhanced with Live Visuals
"""
import os, sys, json, subprocess, threading, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8000
LIVE_PATH = os.path.join(WORKSPACE, "validation", "live_designs.json")

run_state = {
    "running": False,
    "output": "Dashboard ready.\nFill in the design brief and click Run Optimisation.\n",
    "completed": False,
    "error": False,
}


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): return

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":                self._html()
        elif path == "/status":        self._json(run_state)
        elif path == "/live_designs":  self._live_designs()
        elif path.startswith("/plots/"): self._plot(os.path.basename(path))
        else: self.send_error(404)

    def do_POST(self):
        if self.path == "/run":
            n = int(self.headers.get("Content-Length", 0))
            params = json.loads(self.rfile.read(n).decode())
            self._start(params)
            self._json({"queued": True})
        else: self.send_error(404)

    def _json(self, obj):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _live_designs(self):
        try:
            with open(LIVE_PATH) as f:
                data = json.load(f)
        except Exception:
            data = {"total": 0, "evaluated": 0, "designs": [], "best_so_far": None, "mcp_best": None}
        self._json(data)

    def _plot(self, fn):
        p = os.path.join(WORKSPACE, "validation", "plots", fn)
        if os.path.exists(p):
            with open(p, "rb") as f: data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else: self.send_error(404)

    def _start(self, params):
        global run_state
        if run_state["running"]: return
        run_state.update(running=True, completed=False, error=False,
                         output="Starting optimisation pipeline...\n")
        threading.Thread(target=_worker, args=(params,), daemon=True).start()

    def _html(self):
        html = _HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)


def _worker(params):
    global run_state
    try:
        runner = os.path.join(WORKSPACE, "orchestrator", "run_local_opt.py")
        cmd = [sys.executable, "-u", runner,
               "--loa_min",   str(params.get("loa_min", 100)),
               "--loa_max",   str(params.get("loa_max", 200)),
               "--speed",     str(params.get("speed", 14.5)),
               "--n_samples", str(params.get("n_samples", 20)),
               "--ship_type", str(params.get("ship_type", "bulk_carrier")),
               "--bow_type",  str(params.get("bow_type", "bulbous"))]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace",
                                bufsize=1, cwd=WORKSPACE)
        for line in proc.stdout:
            run_state["output"] += line
        proc.wait()
        if proc.returncode == 0:
            run_state["output"] += "\n[DONE] Optimisation complete.\n"
            run_state["completed"] = True
        else:
            run_state["output"] += f"\n[ERROR] Exit code {proc.returncode}\n"
            run_state["error"] = True
    except Exception as e:
        run_state["output"] += f"\n[EXCEPTION] {e}\n"
        run_state["error"] = True
    finally:
        run_state["running"] = False


# ─────────────────────────────────────────────────────────────────────────────
# HTML + CSS + JS  (raw string – no f-string so curly braces are literal JS)
# ─────────────────────────────────────────────────────────────────────────────
_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MCP-ShipForge Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg:#060c18; --bg2:#0f1829; --bg3:#162035; --bg4:#1c2844;
  --border:rgba(79,130,255,.13); --border2:rgba(79,130,255,.22);
  --blue:#4f7bff; --green:#34d399; --red:#ef4444; --amber:#f59e0b; --purple:#a78bfa;
  --text:#e2e8f0; --muted:#6b7280; --dim:#374151;
  --mono:'JetBrains Mono',monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;
     min-height:100vh;display:flex;flex-direction:column;overflow-x:hidden}

/* ── HEADER ── */
header{
  background:linear-gradient(90deg,#080f20,#0f1829);
  border-bottom:1px solid var(--border);
  padding:0 1.5rem; height:54px;
  display:flex;align-items:center;gap:.8rem;flex-shrink:0;
  position:sticky;top:0;z-index:100;
}
.logo{width:34px;height:34px;border-radius:9px;flex-shrink:0;
      background:linear-gradient(135deg,#4f7bff,#34d399);
      display:flex;align-items:center;justify-content:center;
      font-weight:800;font-size:13px;color:#fff;
      box-shadow:0 0 14px rgba(79,123,255,.4)}
.htitle{font-size:15px;font-weight:700;
        background:linear-gradient(90deg,#93c5fd,#6ee7b7);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hsub{font-size:11px;color:var(--muted)}
.hspace{flex:1}
#pill{display:flex;align-items:center;gap:5px;padding:5px 11px;border-radius:999px;
      font-size:11px;font-weight:600;border:1px solid;transition:all .3s}
.pill-idle{background:rgba(107,114,128,.1);color:var(--muted);border-color:rgba(107,114,128,.3)}
.pill-run{background:rgba(79,123,255,.12);color:var(--blue);border-color:rgba(79,123,255,.35)}
.pill-done{background:rgba(52,211,153,.1);color:var(--green);border-color:rgba(52,211,153,.35)}
.pill-err{background:rgba(239,68,68,.1);color:var(--red);border-color:rgba(239,68,68,.35)}
.dot{width:7px;height:7px;border-radius:50%;background:currentColor}
.blink{animation:blink 1.2s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

/* ── MAIN GRID ── */
.main{display:grid;grid-template-columns:340px 1fr 330px;gap:1rem;
      padding:1rem;flex:1;min-height:0}
@media(max-width:1100px){.main{grid-template-columns:300px 1fr}}
@media(max-width:800px){.main{grid-template-columns:1fr}}

/* ── PANELS ── */
.panel{background:var(--bg2);border:1px solid var(--border);
       border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.ph{padding:10px 16px;border-bottom:1px solid var(--border);
    font-size:11px;font-weight:600;color:#64748b;letter-spacing:.06em;
    text-transform:uppercase;display:flex;align-items:center;gap:6px;flex-shrink:0}
.ph .icon{font-size:13px}
.pb{padding:14px 16px;flex:1;overflow:auto}

/* ── FORM ── */
.fgroup{margin-bottom:13px}
label{display:block;font-size:11px;font-weight:500;color:var(--muted);margin-bottom:4px;letter-spacing:.03em}
input,select{width:100%;background:var(--bg3);border:1px solid var(--border);
             border-radius:8px;color:var(--text);font-size:13px;
             font-family:var(--mono);padding:7px 10px;outline:none;transition:border-color .2s}
input:focus,select:focus{border-color:var(--blue)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.note{font-size:10px;color:#4b5563;margin-top:3px;line-height:1.4}
.infobox{background:rgba(79,123,255,.06);border:1px solid rgba(79,123,255,.18);
         border-radius:9px;padding:10px 12px;margin-bottom:12px;font-size:11.5px;
         line-height:1.7;color:#7a96c8}
.infobox strong{color:#b0c4e8}
.tag{display:inline-block;border-radius:4px;padding:0 5px;font-size:10px;font-weight:600;
     margin-left:3px;vertical-align:middle;border:1px solid}
.tag-ok{background:rgba(52,211,153,.1);color:var(--green);border-color:rgba(52,211,153,.3)}
.tag-warn{background:rgba(245,158,11,.08);color:var(--amber);border-color:rgba(245,158,11,.25)}
.runbtn{width:100%;padding:10px;border-radius:9px;border:none;cursor:pointer;font-weight:700;
        font-size:14px;color:#fff;background:linear-gradient(135deg,#4f7bff,#34d399);
        transition:opacity .2s,transform .15s;margin-top:4px}
.runbtn:hover:not(:disabled){opacity:.85;transform:translateY(-1px)}
.runbtn:disabled{opacity:.4;cursor:not-allowed;transform:none}

/* ── PROGRESS ── */
.progbar-wrap{margin:8px 0 4px;background:var(--bg3);border-radius:999px;
              height:5px;overflow:hidden}
.progbar{height:100%;border-radius:999px;transition:width .4s;
         background:linear-gradient(90deg,#4f7bff,#34d399);width:0%}
.progtext{font-size:11px;color:var(--muted);margin-top:3px;font-family:var(--mono)}

/* ── LOG ── */
#log{flex:1;background:#040810;border:1px solid rgba(255,255,255,.05);
     border-radius:9px;color:#6ee7b7;font-family:var(--mono);font-size:11px;
     line-height:1.65;padding:10px;resize:none;outline:none;
     overflow-y:auto;white-space:pre;min-height:200px;max-height:280px}

/* ── CHARTS ── */
.chart-wrap{position:relative;padding:14px 14px 6px}
.chart-wrap canvas{border-radius:8px}

/* ── HULL CANVAS ── */
.hull-canvas-wrap{position:relative;background:var(--bg3);
                  border-radius:10px;overflow:hidden;margin-bottom:6px}
.hull-label{position:absolute;top:6px;left:8px;font-size:9px;font-weight:600;
            color:#4b5563;letter-spacing:.06em;text-transform:uppercase;
            font-family:var(--mono)}
.hull-legend{position:absolute;top:6px;right:8px;font-size:9px;
             font-family:var(--mono);color:var(--muted);text-align:right}
canvas.hc{display:block;width:100%}

/* ── METRIC CHIPS ── */
.chips{display:flex;flex-wrap:wrap;gap:6px;padding:10px 14px}
.chip{background:var(--bg3);border:1px solid var(--border);border-radius:8px;
      padding:8px 12px;min-width:100px}
.chip-l{font-size:10px;color:var(--muted);margin-bottom:2px}
.chip-v{font-size:17px;font-weight:700;font-family:var(--mono);color:#fff}
.chip-u{font-size:10px;color:var(--muted);margin-top:1px}
.chip-v.good{color:var(--green)} .chip-v.bad{color:var(--red)} .chip-v.warn{color:var(--amber)}

/* ── BENCHMARK PLOTS ── */
.bplots{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px 14px}
.bplot{background:var(--bg3);border-radius:9px;overflow:hidden;border:1px solid var(--border)}
.bplot p{font-size:10px;color:var(--muted);padding:6px 8px;border-bottom:1px solid var(--border)}
.bplot img{width:100%;display:block}

/* ── COMPARISON BAR ── */
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px 14px}
.cmp-card{border-radius:9px;padding:10px 12px;border:1px solid}
.cmp-baseline{background:rgba(239,68,68,.05);border-color:rgba(239,68,68,.2)}
.cmp-mcp{background:rgba(52,211,153,.05);border-color:rgba(52,211,153,.2)}
.cmp-title{font-size:10px;font-weight:700;letter-spacing:.05em;margin-bottom:6px}
.cmp-row{font-size:11px;color:var(--muted);display:flex;justify-content:space-between;margin:2px 0}
.cmp-row span{font-family:var(--mono);font-weight:600;color:var(--text)}

.hidden{display:none}
</style>
</head>
<body>
<header>
  <div class="logo">SF</div>
  <div><div class="htitle">MCP-ShipForge</div><div class="hsub">Co-Optimisation Dashboard</div></div>
  <div class="hspace"></div>
  <div id="pill" class="pill-idle"><span class="dot" id="pdot"></span><span id="ptxt">IDLE</span></div>
</header>

<div class="main">

<!-- ═══════════════════════════════ LEFT COL ═══════════════════════════════ -->
<div style="display:flex;flex-direction:column;gap:.8rem">

  <div class="panel">
    <div class="ph"><span class="icon">⚙</span> SHIP DESIGN BRIEF — INPUT</div>
    <div class="pb">
      <div class="infobox">
        <strong>What runs:</strong> Latin Hypercube sampling generates N hull configs.
        Each is evaluated by a 7-step pipeline. Pareto front selects optimal trade-off.<br>
        <strong>Resistance:</strong> Holtrop-Mennen empirical<span class="tag tag-warn">not OpenFOAM</span><br>
        <strong>Structural:</strong> Hull-girder beam theory<span class="tag tag-warn">not FE solver</span><br>
        <strong>Fatigue:</strong> GBR surrogate (R²=0.71)<span class="tag tag-ok">ML</span><br>
        <strong>Rules:</strong> DNV-GL Pt.3 Ch.1 equations<span class="tag tag-ok">real</span>
      </div>
      <div class="fgroup">
        <label>Ship Type</label>
        <select id="ship_type">
          <option value="bulk_carrier">Bulk Carrier (Handymax)</option>
          <option value="container">Container Ship</option>
          <option value="tanker">Oil Tanker</option>
        </select>
      </div>
      <div class="fgroup row2">
        <div><label>LOA Min (m)</label><input type="number" id="loa_min" value="100" min="60" max="350" step="5"></div>
        <div><label>LOA Max (m)</label><input type="number" id="loa_max" value="200" min="60" max="350" step="5"></div>
      </div>
      <p class="note" style="margin:-8px 0 10px">Beam and Draft derived from L/B and B/T ratios. Cb sampled 0.60–0.82.</p>
      <div class="fgroup row2">
        <div><label>Speed (kn)</label><input type="number" id="speed" value="14.5" min="8" max="30" step="0.5"></div>
        <div><label>LHS Designs</label><input type="number" id="n_samples" value="20" min="5" max="100" step="5"></div>
      </div>
      <div class="fgroup">
        <label>Bow Type</label>
        <select id="bow_type">
          <option value="bulbous">Bulbous (lower wave drag, Fn 0.16–0.24)</option>
          <option value="conventional">Conventional</option>
        </select>
      </div>
      <button class="runbtn" id="runbtn" onclick="startRun()">Run Co-Optimisation Pipeline</button>
    </div>
  </div>

  <div class="panel" style="flex:1">
    <div class="ph"><span class="icon">▶</span> LIVE PIPELINE LOG
      <span id="prog-text" class="progtext" style="margin-left:auto"></span>
    </div>
    <div class="pb" style="padding:10px;display:flex;flex-direction:column;gap:6px">
      <div class="progbar-wrap"><div class="progbar" id="progbar"></div></div>
      <textarea id="log" readonly></textarea>
    </div>
  </div>

</div>

<!-- ═══════════════════════════════ CENTRE COL ══════════════════════════════ -->
<div style="display:flex;flex-direction:column;gap:.8rem">

  <!-- Live Scatter -->
  <div class="panel">
    <div class="ph"><span class="icon">◉</span> LIVE DESIGN SPACE EXPLORATION
      <span style="margin-left:auto;font-size:10px;color:#4b5563">
        Green = stability PASS · Red = stability FAIL · ◯ = Pareto-optimal
      </span>
    </div>
    <div class="chart-wrap" style="height:310px">
      <canvas id="scatter-chart"></canvas>
    </div>
  </div>

  <!-- Resistance-Speed Curve -->
  <div class="panel">
    <div class="ph"><span class="icon">〜</span> RESISTANCE vs SPEED CURVE
      <span style="margin-left:auto;font-size:10px;color:#4b5563">
        Computed from Holtrop-Mennen for current best hull
      </span>
    </div>
    <div class="chart-wrap" style="height:220px">
      <canvas id="speed-chart"></canvas>
    </div>
  </div>

  <!-- Comparison (shown after run) -->
  <div class="panel hidden" id="cmp-panel">
    <div class="ph"><span class="icon">⇄</span> SEQUENTIAL BASELINE vs MCP-SHIPFORGE OPTIMAL</div>
    <div class="cmp" id="cmp-cards"></div>
  </div>

  <!-- Result metrics (shown after run) -->
  <div class="panel hidden" id="result-panel">
    <div class="ph"><span class="icon">★</span> OPTIMAL DESIGN — OUTPUT</div>
    <div class="chips" id="chips"></div>
  </div>

  <!-- Benchmark plots -->
  <div class="panel">
    <div class="ph"><span class="icon">■</span> BENCHMARK PLOTS (from last run)</div>
    <div class="bplots">
      <div class="bplot"><p>Pareto Frontier</p><img src="/plots/pareto_frontier.png" onerror="this.parentElement.style.display='none'"></div>
      <div class="bplot"><p>Workflow Ablation</p><img src="/plots/ablation_comparison.png" onerror="this.parentElement.style.display='none'"></div>
      <div class="bplot"><p>ML Surrogate R²=0.71</p><img src="/plots/surrogate_correlation.png" onerror="this.parentElement.style.display='none'"></div>
      <div class="bplot"><p>Architecture</p><img src="/plots/architecture_flowchart.png" onerror="this.parentElement.style.display='none'"></div>
    </div>
  </div>

</div>

<!-- ═══════════════════════════════ RIGHT COL ═══════════════════════════════ -->
<div style="display:flex;flex-direction:column;gap:.8rem">

  <div class="panel">
    <div class="ph"><span class="icon">◈</span> HULL SHAPE — WATERPLANE (TOP VIEW)</div>
    <div class="pb" style="padding:10px">
      <div class="hull-canvas-wrap" style="height:180px">
        <div class="hull-label">PLAN VIEW</div>
        <div class="hull-legend" id="plan-legend"></div>
        <canvas class="hc" id="cv-plan" height="180"></canvas>
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="ph"><span class="icon">◈</span> HULL SHAPE — MIDSHIP SECTION</div>
    <div class="pb" style="padding:10px">
      <div class="hull-canvas-wrap" style="height:200px">
        <div class="hull-label">BODY PLAN (x=0)</div>
        <div class="hull-legend" id="mid-legend"></div>
        <canvas class="hc" id="cv-mid" height="200"></canvas>
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="ph"><span class="icon">◈</span> HULL SHAPE — PROFILE (SIDE VIEW)</div>
    <div class="pb" style="padding:10px">
      <div class="hull-canvas-wrap" style="height:160px">
        <div class="hull-label">STARBOARD PROFILE</div>
        <canvas class="hc" id="cv-prof" height="160"></canvas>
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="ph"><span class="icon">◈</span> RESISTANCE BREAKDOWN</div>
    <div class="chart-wrap" style="height:180px">
      <canvas id="breakdown-chart"></canvas>
    </div>
  </div>

</div>
</div><!-- /main -->

<script>
// ══════════════════════════════════════════════════════
// HULL SERIES-60 MATH (same formula as Python backend)
// ══════════════════════════════════════════════════════
function px(Cb){ return Math.max(1.1, Cb / (1 - Cb + 0.05)); }
function pz(){ return 6.0; }

function wpHB(xn, Cb){ // waterplane half-breadth fraction (0..0.5)
  return 0.5 * (1 - Math.pow(Math.abs(xn), px(Cb)));
}
function midHB(zn){ // midship half-breadth fraction (0..0.5)
  return 0.5 * (1 - Math.pow(Math.abs(zn), pz()));
}

// Holtrop-Mennen resistance in kN for a given hull at speed kn
function hmResistance(loa, beam, draft, Cb, bow, speedKn){
  const V   = speedKn * 0.51444;
  const g   = 9.81, rho = 1025, nu = 1.188e-6;
  const Re  = V * loa / nu;
  const Fn  = V / Math.sqrt(g * loa);
  const S   = 1.025 * loa * (Cb * beam + 1.7 * draft);
  const Cf  = Re > 1 ? 0.075 / Math.pow(Math.log10(Re) - 2, 2) : 0;
  const ff  = 1 + 0.4*(beam/loa) + 2*Math.pow(beam/loa, 2);
  const cpk = 0.014 * Cb * Cb;
  const bulb= (bow === 'bulbous' && Fn > 0.15 && Fn < 0.28) ? 0.18 : 0;
  const Cw  = Math.max(0, cpk * Math.exp(-Math.pow((Fn-0.32)/0.07,2)) * (1-bulb));
  const Ct  = Cf * ff + Cw + 0.0004;
  return { total: 0.5*rho*S*V*V*Ct/1000,
           friction: 0.5*rho*S*V*V*Cf*ff/1000,
           wave: 0.5*rho*S*V*V*Cw/1000,
           Fn: Fn };
}

// ══════════════════════════════════════════════════════
// CANVAS HULL DRAWINGS
// ══════════════════════════════════════════════════════
const BG = '#070c18', BLUE = '#4f7bff', GREEN = '#34d399', RED = '#ef4444';
const GHOST = 'rgba(239,68,68,0.35)';  // baseline ghost colour

function fillBg(ctx, W, H){ ctx.fillStyle=BG; ctx.fillRect(0,0,W,H); }

function drawPlanView(cid, hull, ghostHull){
  const cv = document.getElementById(cid);
  if(!cv) return;
  // Set canvas pixel size from layout size
  cv.width  = cv.offsetWidth  || cv.parentElement.clientWidth  || 300;
  cv.height = cv.offsetHeight || 180;
  const ctx = cv.getContext('2d'), W = cv.width, H = cv.height;
  fillBg(ctx, W, H);
  if(!hull) return;

  function drawWP(h, strokeCol, fillCol, lineW){
    const { loa, beam, Cb, bow_type } = h;
    const mx=28, my=18, n=200;
    const scX = (W-2*mx)/loa, scY = (H-2*my)/beam;
    const sc = Math.min(scX, scY);
    const sL = loa*sc, sB = beam*sc;
    const ox = (W-sL)/2, oy = H/2;
    const tx = t  => ox + t*sL;          // fraction of LOA → x
    const ty = f  => oy - f*sB;          // fraction of beam → y

    ctx.beginPath();
    for(let i=0;i<=n;i++){
      const t=i/n, xn=t*2-1;
      ctx.lineTo(tx(t), ty(wpHB(xn, Cb)));
    }
    for(let i=n;i>=0;i--){
      const t=i/n, xn=t*2-1;
      ctx.lineTo(tx(t), ty(-wpHB(xn, Cb)));
    }
    ctx.closePath();
    const g = ctx.createLinearGradient(ox,oy-sB/2,ox,oy+sB/2);
    g.addColorStop(0, fillCol+'44'); g.addColorStop(0.5, fillCol+'22'); g.addColorStop(1, fillCol+'44');
    ctx.fillStyle=g; ctx.fill();
    ctx.strokeStyle=strokeCol; ctx.lineWidth=lineW; ctx.stroke();

    // Bulb
    if(bow_type==='bulbous'){
      const bx=tx(1)+sc*loa*0.025, br=sc*beam*0.035;
      ctx.beginPath(); ctx.arc(bx,oy,br,0,Math.PI*2);
      ctx.strokeStyle=strokeCol; ctx.lineWidth=1; ctx.stroke();
    }

    // Frames
    ctx.strokeStyle=strokeCol+'44'; ctx.lineWidth=0.5;
    for(let s=0.1;s<1;s+=0.1){
      const xn=s*2-1, hb=wpHB(xn,Cb);
      ctx.beginPath(); ctx.moveTo(tx(s),ty(hb)); ctx.lineTo(tx(s),ty(-hb)); ctx.stroke();
    }
    return {tx, ty, sc, sL, sB, ox, oy};
  }

  // Ghost baseline first
  if(ghostHull) drawWP(ghostHull, RED, RED, 1.2);
  // Active hull
  const r = drawWP(hull, BLUE, BLUE, 2);
  const {tx,ty,sL,oy} = r;
  // Centreline
  ctx.beginPath(); ctx.setLineDash([5,3]);
  ctx.strokeStyle='rgba(99,130,255,.3)'; ctx.lineWidth=1;
  ctx.moveTo(tx(0),oy); ctx.lineTo(tx(1),oy); ctx.stroke(); ctx.setLineDash([]);
  // Labels
  ctx.fillStyle='#4b5563'; ctx.font='9px monospace'; ctx.textAlign='center';
  ctx.fillText('BOW',tx(1)-20,oy-8);
  ctx.fillText('↑ STB',tx(.5),ty(0.5)+10);
  ctx.fillStyle='#374151'; ctx.fillText(`LOA ${hull.loa}m  B ${hull.beam.toFixed(1)}m  Cb ${hull.Cb}`,W/2,H-4);

  document.getElementById('plan-legend').textContent =
    `LOA ${hull.loa}m · B ${hull.beam.toFixed(1)}m`;
}

function drawMidship(cid, hull, ghostHull){
  const cv = document.getElementById(cid);
  if(!cv) return;
  cv.width  = cv.offsetWidth  || 300;
  cv.height = cv.offsetHeight || 200;
  const ctx = cv.getContext('2d'), W = cv.width, H = cv.height;
  fillBg(ctx, W, H);
  if(!hull) return;

  function drawSection(h, strokeCol, fillCol, lineW){
    const { beam, draft } = h;
    const mx=40, my=20;
    const scX=(W-2*mx)/beam, scY=(H-2*my)/draft;
    const sc=Math.min(scX,scY);
    const sB=beam*sc, sD=draft*sc;
    const cx2=W/2, topY=my+(H-2*my-sD)/2;
    const tx = hb => cx2 + hb*sc;
    const ty = d  => topY + d*sc;
    const n=100;
    ctx.beginPath();
    ctx.moveTo(tx(0),ty(0));
    for(let i=0;i<=n;i++){
      const zn=-(i/n), d=-zn*draft;
      ctx.lineTo(tx(beam*midHB(zn)), ty(d));
    }
    ctx.lineTo(tx(0),ty(draft));
    for(let i=n;i>=0;i--){
      const zn=-(i/n), d=-zn*draft;
      ctx.lineTo(tx(-beam*midHB(zn)), ty(d));
    }
    ctx.closePath();
    const g=ctx.createLinearGradient(0,topY,0,topY+sD);
    g.addColorStop(0,fillCol+'33'); g.addColorStop(1,fillCol+'11');
    ctx.fillStyle=g; ctx.fill();
    ctx.strokeStyle=strokeCol; ctx.lineWidth=lineW; ctx.stroke();
    return {tx,ty,cx2,topY,sD,sB};
  }

  if(ghostHull) drawSection(ghostHull, RED, RED, 1.2);
  const r = drawSection(hull, BLUE, BLUE, 2);
  const {tx,ty,cx2,topY,sD} = r;

  // Waterline
  ctx.beginPath(); ctx.setLineDash([5,3]);
  ctx.strokeStyle='#60a5fa'; ctx.lineWidth=1;
  ctx.moveTo(cx2-hull.beam/2*Math.min((W-80)/hull.beam,(H-40)/hull.draft)-10, topY);
  ctx.lineTo(cx2+hull.beam/2*Math.min((W-80)/hull.beam,(H-40)/hull.draft)+10, topY);
  ctx.stroke(); ctx.setLineDash([]);

  // Keel
  ctx.beginPath(); ctx.strokeStyle=RED; ctx.lineWidth=2.5;
  ctx.moveTo(cx2-6, topY+sD); ctx.lineTo(cx2+6, topY+sD); ctx.stroke();

  // Labels
  ctx.fillStyle='#60a5fa'; ctx.font='9px monospace'; ctx.textAlign='left';
  ctx.fillText('WL',6,topY+4);
  ctx.fillStyle=RED; ctx.fillText('K',6,topY+sD+4);

  // Beam arrow
  const sc=Math.min((W-80)/hull.beam,(H-40)/hull.draft);
  ctx.fillStyle='#4b5563'; ctx.textAlign='center';
  ctx.fillText(`B=${hull.beam.toFixed(1)}m · T=${hull.draft.toFixed(1)}m`, W/2, H-4);

  document.getElementById('mid-legend').textContent = `Cb ${hull.Cb}`;
}

function drawProfile(cid, hull, ghostHull){
  const cv = document.getElementById(cid);
  if(!cv) return;
  cv.width  = cv.offsetWidth  || 300;
  cv.height = cv.offsetHeight || 160;
  const ctx = cv.getContext('2d'), W = cv.width, H = cv.height;
  fillBg(ctx, W, H);
  if(!hull) return;

  function drawPro(h, strokeCol, fillCol, lineW){
    const { loa, draft, Cb, bow_type } = h;
    const freeboard = draft*0.4, totalD = draft+freeboard;
    const mx=20,my=10;
    const scX=(W-2*mx)/loa, scY=(H-2*my)/totalD;
    const sc=Math.min(scX,scY);
    const sL=loa*sc, sD=draft*sc, sF=freeboard*sc;
    const ox=(W-sL)/2;
    const wl=my+(H-2*my-totalD*sc)/2+sF;  // waterline y
    const tx = pos => ox+pos*sc;  // 0=stern,loa=bow
    const ty = d => wl+d*sc;      // 0=WL, +draft=keel

    ctx.beginPath();
    // Sheer line (deck)
    ctx.moveTo(tx(0),ty(-freeboard*1.05));
    for(let i=0;i<=200;i++){
      const pos=(i/200)*loa, t=pos/loa;
      const sheer=0.12*(1-4*Math.pow(t-0.5,2));
      ctx.lineTo(tx(pos), ty(-freeboard*(1+sheer)));
    }
    // Bow
    ctx.lineTo(tx(loa), ty(0));
    if(bow_type==='bulbous'){
      const bl=loa*0.035;
      ctx.bezierCurveTo(tx(loa+bl),ty(0),tx(loa+bl),ty(draft*.35),tx(loa),ty(draft*.6));
    }
    ctx.lineTo(tx(loa),ty(draft));
    // Keel
    ctx.lineTo(tx(0),ty(draft*0.97));
    ctx.closePath();
    const g=ctx.createLinearGradient(0,wl-sF,0,wl+sD);
    g.addColorStop(0,fillCol+'11'); g.addColorStop(0.4,fillCol+'33'); g.addColorStop(1,fillCol+'11');
    ctx.fillStyle=g; ctx.fill();
    ctx.strokeStyle=strokeCol; ctx.lineWidth=lineW; ctx.stroke();
    return {tx,ty,wl,sL,sD,ox};
  }

  if(ghostHull) drawPro(ghostHull, RED, RED, 1.2);
  const r = drawPro(hull, BLUE, BLUE, 2);
  const {tx,ty,wl,sL,ox} = r;

  // Waterline
  ctx.beginPath(); ctx.setLineDash([6,3]);
  ctx.strokeStyle='#60a5fa'; ctx.lineWidth=1;
  ctx.moveTo(ox-10,wl); ctx.lineTo(ox+sL+15,wl); ctx.stroke(); ctx.setLineDash([]);

  // Labels
  ctx.fillStyle='#4b5563'; ctx.font='9px monospace'; ctx.textAlign='center';
  ctx.fillText(`LOA ${hull.loa}m`,W/2,H-3);
  ctx.fillStyle='#60a5fa'; ctx.textAlign='right';
  ctx.fillText('WL',ox-3,wl+3);
}

// ══════════════════════════════════════════════════════
// CHART.JS SETUP
// ══════════════════════════════════════════════════════
Chart.defaults.color = '#6b7280';
Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
Chart.defaults.font.family = "'JetBrains Mono', monospace";
Chart.defaults.font.size = 11;

// Scatter chart
const scatterCtx = document.getElementById('scatter-chart').getContext('2d');
const scatterChart = new Chart(scatterCtx, {
  type: 'scatter',
  data: {
    datasets: [
      { label: 'Stability PASS', data: [], backgroundColor: 'rgba(52,211,153,0.75)',
        pointRadius: 6, pointHoverRadius: 8 },
      { label: 'Stability FAIL', data: [], backgroundColor: 'rgba(239,68,68,0.65)',
        pointRadius: 6, pointHoverRadius: 8 },
      { label: 'Pareto Front', data: [], backgroundColor: 'rgba(0,0,0,0)',
        borderColor: '#f59e0b', pointRadius: 12, pointHoverRadius: 14,
        borderWidth: 2, showLine: true, lineTension: 0.3, fill: false,
        pointStyle: 'circle' }
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    animation: { duration: 400 },
    scales: {
      x: { title: { display: true, text: 'Section Weight Index (kg/m²)', color: '#4b5563' },
           grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4b5563' } },
      y: { title: { display: true, text: 'Resistance at Design Speed (kN)', color: '#4b5563' },
           grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4b5563' } }
    },
    plugins: {
      legend: { labels: { color: '#6b7280', boxWidth: 12, padding: 14 } },
      tooltip: {
        callbacks: {
          label: ctx => {
            const d = ctx.raw._d;
            if(!d) return `(${ctx.raw.x.toFixed(1)}, ${ctx.raw.y.toFixed(1)})`;
            return [
              `${d.id}: LOA=${d.hull.loa}m B=${d.hull.beam.toFixed(1)}m T=${d.hull.draft.toFixed(1)}m`,
              `Resistance: ${d.resistance_kN.toFixed(1)} kN   Froude: ${d.froude}`,
              `Weight idx: ${d.weight_index.toFixed(1)} kg/m²`,
              `Stability: ${d.stability_pass?'PASS':'FAIL'}  FEA: ${d.fea_pass?'PASS':'FAIL'}`,
            ];
          }
        }
      }
    }
  }
});

// Speed chart
const speedCtx = document.getElementById('speed-chart').getContext('2d');
const speedChart = new Chart(speedCtx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      { label: 'MCP-ShipForge Optimal', data: [], borderColor: '#34d399',
        backgroundColor: 'rgba(52,211,153,0.08)', fill: true, tension: 0.4,
        pointRadius: 0, borderWidth: 2.5 },
      { label: 'Sequential Baseline (min drag)', data: [], borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,0.06)', fill: true, tension: 0.4,
        pointRadius: 0, borderWidth: 2, borderDash: [5,3] },
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    animation: { duration: 300 },
    scales: {
      x: { title: { display: true, text: 'Speed (knots)', color: '#4b5563' },
           grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4b5563' } },
      y: { title: { display: true, text: 'Resistance (kN)', color: '#4b5563' },
           grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4b5563' } }
    },
    plugins: { legend: { labels: { color: '#6b7280', boxWidth: 12 } },
      annotation: {} }
  }
});

// Breakdown bar chart
const bkCtx = document.getElementById('breakdown-chart').getContext('2d');
const bkChart = new Chart(bkCtx, {
  type: 'bar',
  data: {
    labels: ['Frictional', 'Wave', 'Correlation'],
    datasets: [
      { label: 'Sequential', data: [0,0,0], backgroundColor: 'rgba(239,68,68,0.6)',
        borderColor: '#ef4444', borderWidth: 1 },
      { label: 'MCP Optimal', data: [0,0,0], backgroundColor: 'rgba(52,211,153,0.6)',
        borderColor: '#34d399', borderWidth: 1 },
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    animation: { duration: 300 },
    scales: {
      x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4b5563' } },
      y: { title: { display: true, text: 'Force (kN)', color: '#4b5563' },
           grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#4b5563' } }
    },
    plugins: { legend: { labels: { color: '#6b7280', boxWidth: 10 } } }
  }
});

// ══════════════════════════════════════════════════════
// SPEED CURVE GENERATOR
// ══════════════════════════════════════════════════════
function computeSpeedCurve(hull, speedMin=5, speedMax=28, steps=24){
  const labels=[], data=[];
  for(let i=0;i<=steps;i++){
    const kn = speedMin + (speedMax-speedMin)*i/steps;
    labels.push(kn.toFixed(1));
    data.push(hmResistance(hull.loa, hull.beam, hull.draft, hull.Cb, hull.bow_type, kn).total);
  }
  return {labels,data};
}

function updateSpeedChart(mcpHull, seqHull, designSpeed){
  const mcp = computeSpeedCurve(mcpHull);
  speedChart.data.labels = mcp.labels;
  speedChart.data.datasets[0].data = mcp.data;
  if(seqHull){
    speedChart.data.datasets[1].data = computeSpeedCurve(seqHull).data;
    speedChart.data.datasets[1].label = `Sequential Baseline (${seqHull.loa}m)`;
  }
  speedChart.data.datasets[0].label = `MCP Optimal (${mcpHull.loa}m)`;
  speedChart.update();
}

// ══════════════════════════════════════════════════════
// UPDATE ALL VISUALS FROM LIVE DATA
// ══════════════════════════════════════════════════════
let lastEval = 0;
let lastMcpHull = null, lastSeqHull = null;

function updateVisuals(live){
  if(!live || !live.designs) return;
  const designs = live.designs;
  if(designs.length === lastEval && lastEval > 0) return;
  lastEval = designs.length;

  // ── Scatter chart ──────────────────────────────────
  const passData=[], failData=[], paretoData=[];
  designs.forEach(d => {
    const pt = { x: d.weight_index, y: d.resistance_kN, _d: d };
    if(d.stability_pass) passData.push(pt); else failData.push(pt);
    if(d.pareto) paretoData.push({x:d.weight_index, y:d.resistance_kN, _d:d});
  });
  // Sort Pareto by weight for clean line
  paretoData.sort((a,b)=>a.x-b.x);
  scatterChart.data.datasets[0].data = passData;
  scatterChart.data.datasets[1].data = failData;
  scatterChart.data.datasets[2].data = paretoData;
  scatterChart.update('active');

  // ── Hull drawings ──────────────────────────────────
  const mcpHull  = live.mcp_best  ? live.mcp_best.hull  : (live.best_so_far ? live.best_so_far.hull : null);
  const seqHull  = live.seq_baseline ? live.seq_baseline.hull : null;

  // Only redraw if hull changed
  const hullKey = mcpHull ? JSON.stringify(mcpHull) : '';
  if(hullKey !== (window._lastHullKey||'')){
    window._lastHullKey = hullKey;
    // Show ghost (sequential baseline) vs MCP optimal
    const ghostHull = (seqHull && mcpHull && JSON.stringify(seqHull) !== JSON.stringify(mcpHull)) ? seqHull : null;
    drawPlanView('cv-plan', mcpHull, ghostHull);
    drawMidship('cv-mid', mcpHull, ghostHull);
    drawProfile('cv-prof', mcpHull, ghostHull);
  }

  // ── Speed curve ────────────────────────────────────
  if(mcpHull && (JSON.stringify(mcpHull) !== JSON.stringify(lastMcpHull) ||
                 JSON.stringify(seqHull)  !== JSON.stringify(lastSeqHull))){
    lastMcpHull = mcpHull; lastSeqHull = seqHull;
    updateSpeedChart(mcpHull, seqHull, live.params ? live.params.speed : 14.5);
  }

  // ── Resistance breakdown ───────────────────────────
  if(live.mcp_best && live.seq_baseline){
    const m = live.mcp_best, s = live.seq_baseline;
    // Approximate breakdown from totals (actual split not always in live data)
    const mFr = m.frictional_kN||0, mWv = m.wave_kN||0, mCa = m.resistance_kN - mFr - mWv;
    const sFr = s.frictional_kN||0, sWv = s.wave_kN||0, sCa = s.resistance_kN - sFr - sWv;
    bkChart.data.datasets[0].data = [sFr, sWv, Math.max(0,sCa)];
    bkChart.data.datasets[1].data = [mFr, mWv, Math.max(0,mCa)];
    bkChart.update();
  }

  // ── Comparison panel ──────────────────────────────
  if(live.mcp_best && live.seq_baseline && live.evaluated === live.total){
    const m = live.mcp_best, s = live.seq_baseline;
    document.getElementById('cmp-panel').classList.remove('hidden');
    document.getElementById('cmp-cards').innerHTML = `
      <div class="cmp-card cmp-baseline">
        <div class="cmp-title" style="color:#ef4444">SEQUENTIAL BASELINE</div>
        <div class="cmp-row">LOA <span>${s.hull.loa} m</span></div>
        <div class="cmp-row">Beam <span>${s.hull.beam.toFixed(1)} m</span></div>
        <div class="cmp-row">Resistance <span>${s.resistance_kN.toFixed(1)} kN</span></div>
        <div class="cmp-row">Stability <span style="color:${s.stability_pass?'#34d399':'#ef4444'}">${s.stability_pass?'PASS':'FAIL'}</span></div>
        <div class="cmp-row">Fatigue Life <span>${s.fatigue_years.toFixed(1)} yrs</span></div>
      </div>
      <div class="cmp-card cmp-mcp">
        <div class="cmp-title" style="color:#34d399">MCP-SHIPFORGE OPTIMAL</div>
        <div class="cmp-row">LOA <span>${m.hull.loa} m</span></div>
        <div class="cmp-row">Beam <span>${m.hull.beam.toFixed(1)} m</span></div>
        <div class="cmp-row">Resistance <span>${m.resistance_kN.toFixed(1)} kN</span></div>
        <div class="cmp-row">Stability <span style="color:${m.stability_pass?'#34d399':'#ef4444'}">${m.stability_pass?'PASS':'FAIL'}</span></div>
        <div class="cmp-row">Fatigue Life <span>${m.fatigue_years.toFixed(1)} yrs</span></div>
      </div>`;

    // Result chips
    document.getElementById('result-panel').classList.remove('hidden');
    function chip(l,v,u,cls=''){
      return `<div class="chip"><div class="chip-l">${l}</div>
              <div class="chip-v ${cls}">${v}</div>
              <div class="chip-u">${u}</div></div>`;
    }
    document.getElementById('chips').innerHTML =
      chip('LOA', m.hull.loa, 'm') +
      chip('Beam', m.hull.beam.toFixed(1), 'm') +
      chip('Draft', m.hull.draft.toFixed(1), 'm') +
      chip('Block Cb', m.hull.Cb, '') +
      chip('Resistance', m.resistance_kN.toFixed(1), 'kN') +
      chip('Froude', m.froude, 'Fn') +
      chip('Plate Thick.', m.plate_t_mm.toFixed(1), 'mm') +
      chip('Hotspot σ', m.hotspot_MPa.toFixed(1), 'MPa') +
      chip('Struct. Util.', m.utilization.toFixed(3), '≤0.85', m.fea_pass?'good':'bad') +
      chip('GM/LOA', m.gm_over_loa.toFixed(4), '≥0.033', m.stability_pass?'good':'bad') +
      chip('Disp.', Math.round(m.displacement_m3).toLocaleString(), 'm³') +
      chip('Fatigue', m.fatigue_years.toFixed(1), 'yrs') +
      chip('DNV', m.dnv_pass?'PASS':'FAIL', '', m.dnv_pass?'good':'bad') +
      chip('Stability', m.stability_pass?'PASS':'FAIL', '', m.stability_pass?'good':'bad');
  }
}

// ══════════════════════════════════════════════════════
// POLLING
// ══════════════════════════════════════════════════════
let pollTimer = null;

function pollStatus(){
  fetch('/status').then(r=>r.json()).then(st=>{
    const log = document.getElementById('log');
    log.value = st.output;
    log.scrollTop = log.scrollHeight;

    const pill=document.getElementById('pill');
    const dot=document.getElementById('pdot');
    const txt=document.getElementById('ptxt');
    pill.className=''; dot.className='dot';

    if(st.running){
      pill.classList.add('pill-run'); dot.classList.add('blink'); txt.textContent='RUNNING';
      document.getElementById('runbtn').disabled=true;
    } else if(st.completed){
      pill.classList.add('pill-done'); txt.textContent='COMPLETE';
      document.getElementById('runbtn').disabled=false;
      if(pollTimer){ clearInterval(pollTimer); pollTimer=null; }
    } else if(st.error){
      pill.classList.add('pill-err'); txt.textContent='ERROR';
      document.getElementById('runbtn').disabled=false;
      if(pollTimer){ clearInterval(pollTimer); pollTimer=null; }
    } else {
      pill.classList.add('pill-idle'); txt.textContent='IDLE';
      document.getElementById('runbtn').disabled=false;
    }
  });
}

function pollLive(){
  fetch('/live_designs').then(r=>r.json()).then(live=>{
    updateVisuals(live);
    // Update progress bar
    if(live.total > 0){
      const pct = Math.round(live.evaluated/live.total*100);
      document.getElementById('progbar').style.width = pct+'%';
      document.getElementById('prog-text').textContent =
        live.evaluated+'/'+live.total+' evaluated';
    }
  }).catch(()=>{});
}

function startRun(){
  const params = {
    ship_type: document.getElementById('ship_type').value,
    loa_min:   parseFloat(document.getElementById('loa_min').value),
    loa_max:   parseFloat(document.getElementById('loa_max').value),
    speed:     parseFloat(document.getElementById('speed').value),
    n_samples: parseInt(document.getElementById('n_samples').value),
    bow_type:  document.getElementById('bow_type').value,
  };
  // Reset
  document.getElementById('result-panel').classList.add('hidden');
  document.getElementById('cmp-panel').classList.add('hidden');
  scatterChart.data.datasets.forEach(d=>d.data=[]);
  scatterChart.update();
  lastEval = 0; lastMcpHull = null; lastSeqHull = null;
  window._lastHullKey = '';
  document.getElementById('progbar').style.width='0%';
  document.getElementById('prog-text').textContent='';
  ['cv-plan','cv-mid','cv-prof'].forEach(id=>{
    const c=document.getElementById(id);
    if(c){const ctx=c.getContext('2d');ctx.fillStyle=BG;ctx.fillRect(0,0,c.width,c.height);}
  });

  fetch('/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(params)})
    .then(()=>{
      if(!pollTimer) pollTimer = setInterval(()=>{ pollStatus(); pollLive(); }, 700);
    });
}

// Draw placeholder hulls on load (using form default values)
function drawPlaceholder(){
  const hull = {
    loa: parseFloat(document.getElementById('loa_min').value||100) +
         (parseFloat(document.getElementById('loa_max').value||200) -
          parseFloat(document.getElementById('loa_min').value||100))*0.5,
    beam: 22, draft: 7.5, Cb: 0.71,
    bow_type: document.getElementById('bow_type').value || 'bulbous'
  };
  setTimeout(()=>{
    drawPlanView('cv-plan', hull, null);
    drawMidship('cv-mid', hull, null);
    drawProfile('cv-prof', hull, null);
    updateSpeedChart(hull, null, 14.5);
  }, 300);
}

window.addEventListener('load', ()=>{
  pollStatus();
  pollLive();
  drawPlaceholder();
  // Update placeholder when form changes
  ['loa_min','loa_max','bow_type'].forEach(id=>{
    document.getElementById(id).addEventListener('change', drawPlaceholder);
  });
});
</script>
</body>
</html>"""


def main():
    print(f"  MCP-ShipForge Dashboard -> http://localhost:{PORT}")
    webbrowser.open(f"http://localhost:{PORT}")
    httpd = HTTPServer(("", PORT), DashboardHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    main()
