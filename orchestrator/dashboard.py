"""
MCP-ShipForge Control Dashboard
================================
A local web dashboard (http://localhost:8000) that:
  1. Accepts a real ship design brief (LOA range, speed, samples, bow type)
  2. Runs run_local_opt.py with those parameters, streaming output live
  3. Displays results JSON and benchmark plots when the run completes

What this does NOT do:
  - Call DeepSeek or any LLM
  - Run real OpenFOAM CFD
  - Use a real FE solver
"""

import os
import sys
import json
import subprocess
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8000

# --------------------------------------------------------------------------- #
# Global run state
# --------------------------------------------------------------------------- #
run_state = {
    "running": False,
    "output": "Dashboard ready.\nFill in the design brief on the left and click Run.\n",
    "completed": False,
    "error": False,
    "results": None,        # dict loaded from results.json after a successful run
    "last_params": {}
}


# --------------------------------------------------------------------------- #
# HTTP handler
# --------------------------------------------------------------------------- #
class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return  # suppress noise

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._serve_html()
        elif path.startswith("/plots/"):
            self._serve_plot(os.path.basename(path))
        elif path == "/status":
            self._json(run_state)
        elif path == "/results":
            data = run_state.get("results") or {}
            self._json(data)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/run":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                params = json.loads(body)
            except Exception:
                params = {}
            self._start_run(params)
            self._json({"queued": True})
        else:
            self.send_error(404)

    # ------------------------------------------------------------------ helpers
    def _json(self, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_plot(self, filename):
        plot_path = os.path.join(WORKSPACE, "validation", "plots", filename)
        if os.path.exists(plot_path):
            with open(plot_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404, "Plot not found – run the optimiser first")

    def _start_run(self, params):
        global run_state
        if run_state["running"]:
            return
        run_state["running"] = True
        run_state["completed"] = False
        run_state["error"] = False
        run_state["results"] = None
        run_state["last_params"] = params
        run_state["output"] = (
            "=================================================================\n"
            "  MCP-ShipForge Local Co-Optimisation Pipeline\n"
            "=================================================================\n\n"
            f"  Ship Type     : {params.get('ship_type', 'bulk_carrier')}\n"
            f"  LOA Range     : {params.get('loa_min', 100)} - {params.get('loa_max', 200)} m\n"
            f"  Design Speed  : {params.get('speed', 14.5)} kn\n"
            f"  LHS Samples   : {params.get('n_samples', 20)}\n"
            f"  Bow Preference: {params.get('bow_type', 'bulbous')}\n\n"
            "Starting pipeline...\n"
        )
        threading.Thread(target=_run_thread, args=(params,), daemon=True).start()

    def _serve_html(self):
        html = _build_html().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)


# --------------------------------------------------------------------------- #
# Background worker
# --------------------------------------------------------------------------- #
def _run_thread(params):
    global run_state
    try:
        runner = os.path.join(WORKSPACE, "orchestrator", "run_local_opt.py")
        cmd = [
            sys.executable, "-u", runner,
            "--loa_min",   str(params.get("loa_min", 100)),
            "--loa_max",   str(params.get("loa_max", 200)),
            "--speed",     str(params.get("speed", 14.5)),
            "--n_samples", str(params.get("n_samples", 20)),
            "--ship_type", str(params.get("ship_type", "bulk_carrier")),
            "--bow_type",  str(params.get("bow_type", "bulbous")),
        ]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=WORKSPACE
        )
        for line in process.stdout:
            run_state["output"] += line

        process.wait()
        if process.returncode == 0:
            run_state["output"] += "\n[DONE] Run complete.\n"
            run_state["completed"] = True
            # Try to load results
            results_path = os.path.join(WORKSPACE, "validation", "results.json")
            if os.path.exists(results_path):
                with open(results_path, "r") as f:
                    run_state["results"] = json.load(f)
        else:
            run_state["output"] += f"\n[ERROR] Process exited with code {process.returncode}\n"
            run_state["error"] = True
    except Exception as e:
        run_state["output"] += f"\n[EXCEPTION] {e}\n"
        run_state["error"] = True
    finally:
        run_state["running"] = False


# --------------------------------------------------------------------------- #
# HTML page
# --------------------------------------------------------------------------- #
def _build_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MCP-ShipForge Dashboard</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg:      #0a0e1a;
      --bg2:     #111827;
      --bg3:     #1a2235;
      --border:  rgba(99,130,255,0.15);
      --accent:  #4f7bff;
      --accent2: #34d399;
      --warn:    #f59e0b;
      --danger:  #ef4444;
      --text:    #e2e8f0;
      --muted:   #6b7280;
      --mono:    'JetBrains Mono', monospace;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif;
           min-height: 100vh; display: flex; flex-direction: column; }

    /* ── top bar ── */
    header {
      background: linear-gradient(90deg, #0f172a 0%, #111827 100%);
      border-bottom: 1px solid var(--border);
      padding: 0 2rem;
      height: 56px;
      display: flex;
      align-items: center;
      gap: 1rem;
      flex-shrink: 0;
    }
    .logo { width:32px; height:32px; background: linear-gradient(135deg,#4f7bff,#34d399);
            border-radius:8px; display:flex; align-items:center; justify-content:center;
            font-weight:700; font-size:13px; color:#fff; flex-shrink:0; }
    .title { font-size:15px; font-weight:600; color:#fff; }
    .subtitle { font-size:12px; color: var(--muted); }
    .pill {
      margin-left: auto;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 600;
      border: 1px solid;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .pill.idle    { background:rgba(107,114,128,.1); color:var(--muted);   border-color:rgba(107,114,128,.3); }
    .pill.running { background:rgba(79,123,255,.12); color:var(--accent);  border-color:rgba(79,123,255,.3);  }
    .pill.done    { background:rgba(52,211,153,.12); color:var(--accent2); border-color:rgba(52,211,153,.3);  }
    .pill.error   { background:rgba(239,68,68,.12);  color:var(--danger);  border-color:rgba(239,68,68,.3);   }
    .dot { width:7px; height:7px; border-radius:50%; background:currentColor; }
    .dot.pulse { animation: pulse 1.4s ease-in-out infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }

    /* ── layout ── */
    .main { display:grid; grid-template-columns:360px 1fr; gap:1.5rem; padding:1.5rem;
            flex:1; min-height:0; }
    @media(max-width:900px){ .main{ grid-template-columns:1fr; } }

    /* ── panels ── */
    .panel {
      background: var(--bg2);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
    }
    .panel-head {
      padding: 14px 20px;
      border-bottom: 1px solid var(--border);
      font-size: 13px;
      font-weight: 600;
      color: #94a3b8;
      letter-spacing: .05em;
      text-transform: uppercase;
    }
    .panel-body { padding: 20px; }

    /* ── form ── */
    .form-group { margin-bottom: 16px; }
    label { display:block; font-size:12px; font-weight:500; color:var(--muted);
            margin-bottom:5px; letter-spacing:.03em; }
    .note { font-size:11px; color:#4b5563; margin-top:3px; }
    input, select {
      width: 100%;
      background: var(--bg3);
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 8px;
      color: var(--text);
      font-size: 13px;
      font-family: var(--mono);
      padding: 8px 12px;
      transition: border-color .2s;
      outline: none;
    }
    input:focus, select:focus { border-color: var(--accent); }
    .row2 { display:grid; grid-template-columns:1fr 1fr; gap:10px; }

    /* honest info box */
    .info-box {
      background: rgba(79,123,255,.07);
      border: 1px solid rgba(79,123,255,.2);
      border-radius: 10px;
      padding: 12px 14px;
      margin-bottom: 16px;
      font-size: 12px;
      line-height: 1.7;
      color: #93a8d8;
    }
    .info-box strong { color: #c7d5f0; }
    .info-box .tag {
      display: inline-block;
      background: rgba(52,211,153,.12);
      color: var(--accent2);
      border: 1px solid rgba(52,211,153,.25);
      border-radius: 4px;
      padding: 0 5px;
      font-size: 10px;
      font-weight: 600;
      margin-left: 4px;
      vertical-align: middle;
    }
    .info-box .tag.warn {
      background: rgba(245,158,11,.1);
      color: var(--warn);
      border-color: rgba(245,158,11,.25);
    }

    .run-btn {
      width: 100%;
      padding: 11px;
      border-radius: 10px;
      border: none;
      background: linear-gradient(135deg, #4f7bff, #34d399);
      color: #fff;
      font-weight: 600;
      font-size: 14px;
      cursor: pointer;
      transition: opacity .2s, transform .1s;
    }
    .run-btn:hover:not(:disabled) { opacity:.88; transform:translateY(-1px); }
    .run-btn:disabled { opacity:.45; cursor:not-allowed; transform:none; }

    /* ── log console ── */
    .log-wrap { display:flex; flex-direction:column; height:280px; }
    #log-console {
      flex:1;
      background: #070b14;
      border: 1px solid rgba(255,255,255,.05);
      border-radius: 10px;
      color: #7ec8a4;
      font-family: var(--mono);
      font-size: 11.5px;
      line-height: 1.6;
      padding: 12px;
      resize: none;
      outline: none;
      overflow-y: auto;
      white-space: pre;
    }

    /* ── right side ── */
    .right-col { display:flex; flex-direction:column; gap:1.5rem; }

    /* result card */
    .result-card {
      display:none;
      background: var(--bg2);
      border: 1px solid rgba(52,211,153,.25);
      border-radius:16px;
      overflow:hidden;
    }
    .result-card.visible { display:block; }
    .result-card .panel-head { border-color: rgba(52,211,153,.2); color: var(--accent2); }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
      gap: 10px;
      padding: 16px 20px;
    }
    .metric {
      background: var(--bg3);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 14px;
    }
    .metric-label { font-size: 11px; color: var(--muted); margin-bottom: 4px; }
    .metric-value { font-size: 18px; font-weight: 700; font-family: var(--mono); color: #fff; }
    .metric-value.good  { color: var(--accent2); }
    .metric-value.bad   { color: var(--danger); }
    .metric-value.warn  { color: var(--warn); }
    .metric-unit { font-size: 11px; color: var(--muted); margin-top: 1px; }

    /* plots */
    .plots-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      padding: 16px 20px;
    }
    .plot-card {
      background: var(--bg3);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
    }
    .plot-label { font-size:11px; color:var(--muted); padding:8px 12px; border-bottom:1px solid var(--border); }
    .plot-card img { width:100%; display:block; }

    /* pipeline legend */
    .pipeline {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 14px 20px;
    }
    .pipeline-step {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      font-size: 12px;
      color: #94a3b8;
    }
    .step-num {
      flex-shrink: 0;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: var(--bg3);
      border: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 10px;
      font-weight: 700;
      color: var(--accent);
    }
    .step-text strong { color: var(--text); }
    .step-text em { color: var(--muted); font-style: normal; font-size: 11px; }

    .divider { height:1px; background:var(--border); margin: 0 20px; }
  </style>
</head>
<body>

<header>
  <div class="logo">SF</div>
  <div>
    <div class="title">MCP-ShipForge</div>
    <div class="subtitle">Agentic Co-Optimisation Dashboard</div>
  </div>
  <div id="status-pill" class="pill idle">
    <span class="dot" id="status-dot"></span>
    <span id="status-text">IDLE</span>
  </div>
</header>

<div class="main">
  <!-- LEFT: form + log -->
  <div style="display:flex;flex-direction:column;gap:1rem;">

    <!-- Input Form -->
    <div class="panel">
      <div class="panel-head">Ship Design Brief — INPUT</div>
      <div class="panel-body">

        <div class="info-box">
          <strong>What this runs:</strong> Latin Hypercube Sampling generates
          <em>N</em> hull configurations. Each is evaluated through a 7-step pipeline
          and a Pareto front selects the best trade-off design.<br><br>
          <strong>CFD:</strong> Holtrop-Mennen empirical formula<span class="tag warn">NOT OpenFOAM</span><br>
          <strong>Structural:</strong> Hull girder beam theory<span class="tag warn">NOT FE solver</span><br>
          <strong>Fatigue:</strong> GBR ML surrogate on synthetic S-N data<span class="tag">ML</span><br>
          <strong>Rules:</strong> DNV-GL Pt.3 Ch.1 equations<span class="tag">Real</span>
        </div>

        <div class="form-group">
          <label>Ship Type</label>
          <select id="ship_type">
            <option value="bulk_carrier">Bulk Carrier (Handymax)</option>
            <option value="container">Container Ship</option>
            <option value="tanker">Tanker</option>
          </select>
        </div>

        <div class="form-group row2">
          <div>
            <label>LOA Min (m)</label>
            <input type="number" id="loa_min" value="100" min="60" max="350" step="5">
          </div>
          <div>
            <label>LOA Max (m)</label>
            <input type="number" id="loa_max" value="200" min="60" max="350" step="5">
          </div>
        </div>
        <p class="note" style="margin-top:-10px;margin-bottom:14px;">
          Beam and draft are derived from LOA using L/B and B/T ratios. Block coefficient Cb is sampled 0.60–0.82.
        </p>

        <div class="form-group row2">
          <div>
            <label>Design Speed (kn)</label>
            <input type="number" id="speed" value="14.5" min="8" max="30" step="0.5">
          </div>
          <div>
            <label>LHS Samples (designs)</label>
            <input type="number" id="n_samples" value="20" min="5" max="100" step="5">
          </div>
        </div>

        <div class="form-group">
          <label>Bow Type Preference</label>
          <select id="bow_type">
            <option value="bulbous">Bulbous (reduces wave resistance at Fn 0.16–0.24)</option>
            <option value="conventional">Conventional</option>
          </select>
        </div>

        <button class="run-btn" id="run-btn" onclick="startRun()">
          Run Co-Optimisation Pipeline
        </button>
      </div>
    </div>

    <!-- Log Console -->
    <div class="panel" style="flex:1;">
      <div class="panel-head">Live Pipeline Log — OUTPUT</div>
      <div class="panel-body" style="padding:12px;">
        <div class="log-wrap">
          <textarea id="log-console" readonly></textarea>
        </div>
      </div>
    </div>

  </div>

  <!-- RIGHT: results + plots -->
  <div class="right-col">

    <!-- Optimal Design Result Card (hidden until run completes) -->
    <div class="result-card" id="result-card">
      <div class="panel-head">Optimal Design — Co-Optimisation Output</div>
      <div class="metrics-grid" id="metrics-grid">
        <!-- filled by JS -->
      </div>
      <div class="divider"></div>
    </div>

    <!-- Pipeline explanation (always visible) -->
    <div class="panel">
      <div class="panel-head">Pipeline — What Each Step Does</div>
      <div class="pipeline">
        <div class="pipeline-step">
          <div class="step-num">1</div>
          <div class="step-text"><strong>LHS Sampling</strong> — generates N hull parameter sets (LOA, Beam, Draft, Cb, Bow) spread evenly across the design space using Latin Hypercube Sampling.</div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">2</div>
          <div class="step-text"><strong>Hull Geometry</strong> — generates a Series-60 parametric waterline curve and exports an ASCII STL mesh file. <em>No CAD software used.</em></div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">3</div>
          <div class="step-text"><strong>Resistance (Holtrop-Mennen)</strong> — computes frictional (ITTC-57), form, and wave resistance. Returns total drag in kN. <em>No OpenFOAM.</em></div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">4</div>
          <div class="step-text"><strong>DNV Scantlings</strong> — calculates wave + static bottom pressure (DNV Pt.3 Ch.1 Sec.6 Eq.6.2), derives minimum plate thickness, checks actual thickness compliance.</div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">5</div>
          <div class="step-text"><strong>Structural Analysis (Beam Theory)</strong> — computes hull girder I_y, neutral axis, hogging/sagging bending moments, global + local bending stress, hotspot stress (SCF = 1.8). <em>Not a FE solver.</em></div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">6</div>
          <div class="step-text"><strong>Fatigue Life (ML Surrogate)</strong> — Gradient Boosting Regressor trained on 15,000 synthetic DNV-RP-C203 S-N curve samples. Predicts log10(cycles to failure). R² = 0.71.</div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">7</div>
          <div class="step-text"><strong>Stability Check</strong> — estimates metacentric height GM using Morrish's formula, computes GM/LOA ratio. Pass criterion: GM/LOA ≥ 0.033 (DNV).</div>
        </div>
      </div>
    </div>

    <!-- Plots -->
    <div class="panel">
      <div class="panel-head">Benchmark Plots (from last benchmark run)</div>
      <div class="plots-grid">
        <div class="plot-card">
          <div class="plot-label">Pareto Frontier — Drag vs Weight vs Fatigue</div>
          <img src="/plots/pareto_frontier.png" alt="Pareto Frontier" onerror="this.style.display='none'">
        </div>
        <div class="plot-card">
          <div class="plot-label">Workflow Ablation Comparison</div>
          <img src="/plots/ablation_comparison.png" alt="Ablation" onerror="this.style.display='none'">
        </div>
        <div class="plot-card">
          <div class="plot-label">ML Surrogate Validation (R² = 0.71)</div>
          <img src="/plots/surrogate_correlation.png" alt="Surrogate" onerror="this.style.display='none'">
        </div>
        <div class="plot-card">
          <div class="plot-label">System Architecture</div>
          <img src="/plots/architecture_flowchart.png" alt="Architecture" onerror="this.style.display='none'">
        </div>
      </div>
    </div>

  </div>
</div>

<script>
let polling = null;

function startRun() {
  const params = {
    ship_type: document.getElementById('ship_type').value,
    loa_min:   parseFloat(document.getElementById('loa_min').value),
    loa_max:   parseFloat(document.getElementById('loa_max').value),
    speed:     parseFloat(document.getElementById('speed').value),
    n_samples: parseInt(document.getElementById('n_samples').value),
    bow_type:  document.getElementById('bow_type').value,
  };

  document.getElementById('run-btn').disabled = true;
  document.getElementById('result-card').classList.remove('visible');
  document.getElementById('log-console').value = 'Submitting job...\\n';

  fetch('/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(params)
  }).then(() => {
    if (!polling) polling = setInterval(pollStatus, 600);
  });
}

function pollStatus() {
  fetch('/status')
    .then(r => r.json())
    .then(state => {
      // Update log
      const el = document.getElementById('log-console');
      el.value = state.output;
      el.scrollTop = el.scrollHeight;

      // Update pill
      const pill = document.getElementById('status-pill');
      const dot  = document.getElementById('status-dot');
      const txt  = document.getElementById('status-text');

      pill.className = 'pill';
      dot.className  = 'dot';

      if (state.running) {
        pill.classList.add('running');
        dot.classList.add('pulse');
        txt.textContent = 'RUNNING';
        document.getElementById('run-btn').disabled = true;
      } else if (state.completed) {
        pill.classList.add('done');
        txt.textContent = 'DONE';
        document.getElementById('run-btn').disabled = false;
        if (polling) { clearInterval(polling); polling = null; }
        loadResults();
      } else if (state.error) {
        pill.classList.add('error');
        txt.textContent = 'ERROR';
        document.getElementById('run-btn').disabled = false;
        if (polling) { clearInterval(polling); polling = null; }
      } else {
        pill.classList.add('idle');
        txt.textContent = 'IDLE';
        document.getElementById('run-btn').disabled = false;
      }
    });
}

function loadResults() {
  fetch('/results')
    .then(r => r.json())
    .then(data => {
      if (!data.best_design) return;
      const b = data.best_design;
      const grid = document.getElementById('metrics-grid');
      grid.innerHTML = '';

      function metric(label, value, unit, cls='') {
        return `<div class="metric">
          <div class="metric-label">${label}</div>
          <div class="metric-value ${cls}">${value}</div>
          <div class="metric-unit">${unit}</div>
        </div>`;
      }

      grid.innerHTML =
        metric('LOA', b.hull.loa, 'm') +
        metric('Beam', b.hull.beam, 'm') +
        metric('Draft', b.hull.draft, 'm') +
        metric('Block Coeff Cb', b.hull.Cb, '') +
        metric('Resistance', b.resistance_kN.toFixed(1), 'kN') +
        metric('Froude No.', b.froude_number, 'Fn') +
        metric('Plate Thickness', b.plate_thickness_mm.toFixed(1), 'mm') +
        metric('Hotspot Stress', b.hotspot_stress_MPa.toFixed(1), 'MPa') +
        metric('Struct. Utilization', b.structural_utilization.toFixed(3),
               '≤ 0.85 = safe', b.fea_passed ? 'good' : 'bad') +
        metric('GM/LOA', b.gm_over_loa.toFixed(4),
               '≥ 0.033 = pass', b.stability_passed ? 'good' : 'bad') +
        metric('Displacement', Math.round(b.displacement_volume_m3).toLocaleString(), 'm³') +
        metric('Fatigue Life', b.fatigue_life_years.toFixed(1), 'yrs') +
        metric('DNV Scantling', b.dnv_scantling_passed ? 'PASS' : 'FAIL', '',
               b.dnv_scantling_passed ? 'good' : 'bad') +
        metric('Stability', b.stability_passed ? 'PASS' : 'FAIL', '',
               b.stability_passed ? 'good' : 'bad') +
        metric('Designs Evaluated', data.total_evaluated, '') +
        metric('Pareto Front', data.pareto_size, 'designs');

      document.getElementById('result-card').classList.add('visible');
    });
}

// Initial poll
pollStatus();
</script>
</body>
</html>"""


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main():
    print("=" * 60)
    print(f"  MCP-ShipForge Dashboard running at: http://localhost:{PORT}")
    print("=" * 60)
    webbrowser.open(f"http://localhost:{PORT}")
    httpd = HTTPServer(("", PORT), DashboardHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        httpd.server_close()


if __name__ == "__main__":
    main()
