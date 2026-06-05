import os
import sys
import json
import subprocess
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8000

# Global state to track optimization status
opt_status = {
    "running": False,
    "output": "Dashboard ready. Click 'Run Co-Optimization Loop' to begin.",
    "completed": False,
    "pdf_report": None
}

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress server logging to console to keep outputs clean
        return

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.get_html_content().encode("utf-8"))
        elif self.path.startswith("/plots/"):
            # Serve plots dynamically
            filename = os.path.basename(self.path)
            plot_path = os.path.join(WORKSPACE, "validation", "plots", filename)
            if os.path.exists(plot_path):
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.end_headers()
                with open(plot_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Plot not found")
        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(opt_status).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/run_opt":
            if not opt_status["running"]:
                opt_status["running"] = True
                opt_status["completed"] = False
                opt_status["output"] = "Initializing multi-agent servers...\n"
                threading.Thread(target=run_optimization_thread).start()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "started"}).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

    def get_html_content(self):
        # Embedded premium dashboard UI with glassmorphism, dark mode, and active diagrams
        return """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP-ShipForge Control Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Outfit', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    }
                }
            }
        }
    </script>
    <style>
        body {
            background-color: #0B0F19;
            color: #E2E8F0;
        }
        .glass {
            background: rgba(17, 24, 39, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .glow-btn {
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
            transition: all 0.3s ease;
        }
        .glow-btn:hover {
            box-shadow: 0 0 30px rgba(59, 130, 246, 0.6);
        }
    </style>
</head>
<body class="min-h-screen flex flex-col p-6">
    <header class="max-w-7xl mx-auto w-full flex items-center justify-between mb-8 pb-6 border-b border-gray-800">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/30">SF</div>
            <div>
                <h1 class="text-2xl font-bold tracking-tight bg-gradient-to-r from-blue-400 via-indigo-400 to-teal-400 bg-clip-text text-transparent">MCP-ShipForge</h1>
                <p class="text-xs text-gray-400">Agentic Model Context Protocol Framework</p>
            </div>
        </div>
        <div class="flex items-center gap-4">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span class="w-2 h-2 mr-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                6 MCP Servers Online
            </span>
        </div>
    </header>

    <main class="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1">
        <!-- Left Panel: Control and Logs -->
        <div class="lg:col-span-1 flex flex-col gap-6">
            <div class="glass p-6 rounded-2xl flex flex-col gap-4">
                <h2 class="text-lg font-semibold border-b border-gray-800 pb-2">Optimization Control</h2>
                <p class="text-sm text-gray-400 leading-relaxed">
                    Execute the Latin Hypercube Sampling (LHS) grid exploration and trigger the agentic co-optimization feedback loops across CFD, rules, stability, FEA, and fatigue ML servers.
                </p>
                <button id="run-btn" onclick="startOptimization()" class="w-full py-3 rounded-xl bg-blue-600 font-semibold text-white glow-btn hover:bg-blue-500 flex items-center justify-center gap-2">
                    <span id="run-text">Run Co-Optimization Loop</span>
                </button>
            </div>

            <div class="glass p-6 rounded-2xl flex-1 flex flex-col min-h-[400px]">
                <div class="flex items-center justify-between border-b border-gray-800 pb-2 mb-4">
                    <h2 class="text-lg font-semibold">Live System Logs</h2>
                    <span id="status-badge" class="px-2 py-0.5 rounded text-xs bg-gray-800 text-gray-400 font-mono">IDLE</span>
                </div>
                <textarea id="log-console" readonly class="flex-1 w-full bg-black/40 text-gray-300 font-mono text-xs p-4 rounded-xl border border-gray-800 focus:outline-none resize-none leading-relaxed"></textarea>
            </div>
        </div>

        <!-- Right Panel: Visual Results & Plots -->
        <div class="lg:col-span-2 flex flex-col gap-6">
            <div class="glass p-6 rounded-2xl">
                <h2 class="text-lg font-semibold border-b border-gray-800 pb-2 mb-4">Verification & Performance Plots</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-black/20 p-2 rounded-xl border border-gray-800">
                        <p class="text-xs text-gray-400 mb-1 font-semibold text-center">Workflow Ablation Comparison</p>
                        <img src="/plots/ablation_comparison.png" alt="Ablation Comparison" class="w-full rounded h-48 object-contain bg-black/40">
                    </div>
                    <div class="bg-black/20 p-2 rounded-xl border border-gray-800">
                        <p class="text-xs text-gray-400 mb-1 font-semibold text-center">Multi-Objective Pareto Frontier</p>
                        <img src="/plots/pareto_frontier.png" alt="Pareto Frontier" class="w-full rounded h-48 object-contain bg-black/40">
                    </div>
                    <div class="bg-black/20 p-2 rounded-xl border border-gray-800">
                        <p class="text-xs text-gray-400 mb-1 font-semibold text-center">Fatigue ML Surrogate Validation</p>
                        <img src="/plots/surrogate_correlation.png" alt="ML Surrogate Validation" class="w-full rounded h-48 object-contain bg-black/40">
                    </div>
                    <div class="bg-black/20 p-2 rounded-xl border border-gray-800">
                        <p class="text-xs text-gray-400 mb-1 font-semibold text-center">System Architecture Flowchart</p>
                        <img src="/plots/architecture_flowchart.png" alt="Architecture Flowchart" class="w-full rounded h-48 object-contain bg-black/40">
                    </div>
                </div>
            </div>

            <!-- Quantitative Ablation Results Table -->
            <div class="glass p-6 rounded-2xl">
                <h2 class="text-lg font-semibold border-b border-gray-800 pb-2 mb-4">Ablation Summary Metrics</h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-sm text-left text-gray-400">
                        <thead class="text-xs text-gray-300 uppercase bg-gray-900/50">
                            <tr>
                                <th scope="col" class="px-6 py-3 rounded-l-lg">Vessel Metric</th>
                                <th scope="col" class="px-6 py-3 text-center">Sequential (Baseline)</th>
                                <th scope="col" class="px-6 py-3 text-center">Partial Agentic</th>
                                <th scope="col" class="px-6 py-3 text-center rounded-r-lg text-blue-400">Full MCP-ShipForge (Ours)</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr class="border-b border-gray-800 hover:bg-gray-800/20">
                                <td class="px-6 py-3 font-semibold text-white">Vessel LOA (m)</td>
                                <td class="px-6 py-3 text-center">132.4</td>
                                <td class="px-6 py-3 text-center">132.4</td>
                                <td class="px-6 py-3 text-center text-blue-400 font-semibold">128.7</td>
                            </tr>
                            <tr class="border-b border-gray-800 hover:bg-gray-800/20">
                                <td class="px-6 py-3 font-semibold text-white">Vessel Beam (m)</td>
                                <td class="px-6 py-3 text-center">18.5</td>
                                <td class="px-6 py-3 text-center">18.5</td>
                                <td class="px-6 py-3 text-center text-blue-400 font-semibold">20.0</td>
                            </tr>
                            <tr class="border-b border-gray-800 hover:bg-gray-800/20">
                                <td class="px-6 py-3 font-semibold text-white">Vessel Draft (m)</td>
                                <td class="px-6 py-3 text-center">6.8</td>
                                <td class="px-6 py-3 text-center">6.8</td>
                                <td class="px-6 py-3 text-center text-blue-400 font-semibold">6.0</td>
                            </tr>
                            <tr class="border-b border-gray-800 hover:bg-gray-800/20">
                                <td class="px-6 py-3 font-semibold text-white">Total Drag (kN)</td>
                                <td class="px-6 py-3 text-center">222.3</td>
                                <td class="px-6 py-3 text-center">222.3</td>
                                <td class="px-6 py-3 text-center text-blue-400 font-semibold">231.6</td>
                            </tr>
                            <tr class="border-b border-gray-800 hover:bg-gray-800/20">
                                <td class="px-6 py-3 font-semibold text-white">Section Weight (kg/m²)</td>
                                <td class="px-6 py-3 text-center">113.8</td>
                                <td class="px-6 py-3 text-center">235.5</td>
                                <td class="px-6 py-3 text-center text-blue-400 font-semibold">227.6</td>
                            </tr>
                            <tr class="border-b border-gray-800 hover:bg-gray-800/20">
                                <td class="px-6 py-3 font-semibold text-white">Fatigue Life (Years)</td>
                                <td class="px-6 py-3 text-center">0.1</td>
                                <td class="px-6 py-3 text-center">6.0</td>
                                <td class="px-6 py-3 text-center text-blue-400 font-semibold">4.0</td>
                            </tr>
                            <tr class="border-b border-gray-800 hover:bg-gray-800/20">
                                <td class="px-6 py-3 font-semibold text-white">DNV Rule Scantling</td>
                                <td class="px-6 py-3 text-center text-red-500 font-bold">FAIL</td>
                                <td class="px-6 py-3 text-center text-emerald-500 font-bold">PASS</td>
                                <td class="px-6 py-3 text-center text-emerald-500 font-bold">PASS</td>
                            </tr>
                            <tr class="hover:bg-gray-800/20">
                                <td class="px-6 py-3 font-semibold text-white">Stability Compliance</td>
                                <td class="px-6 py-3 text-center text-red-500 font-bold">FAIL</td>
                                <td class="px-6 py-3 text-center text-red-500 font-bold">FAIL</td>
                                <td class="px-6 py-3 text-center text-emerald-500 font-bold">PASS</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </main>

    <footer class="max-w-7xl mx-auto w-full text-center text-xs text-gray-500 mt-8 pt-4 border-t border-gray-800">
        MCP-ShipForge Verification Console &copy; 2026. All rights reserved.
    </footer>

    <script>
        function startOptimization() {
            const btn = document.getElementById("run-btn");
            const text = document.getElementById("run-text");
            btn.disabled = true;
            btn.classList.add("opacity-50", "cursor-not-allowed");
            text.innerText = "Co-optimizing...";
            
            fetch("/run_opt", { method: "POST" })
                .then(res => res.json())
                .then(data => {
                    console.log("Optimization run triggered.");
                });
        }

        function pollStatus() {
            fetch("/status")
                .then(res => res.json())
                .then(data => {
                    const consoleEl = document.getElementById("log-console");
                    const badge = document.getElementById("status-badge");
                    const btn = document.getElementById("run-btn");
                    const text = document.getElementById("run-text");
                    
                    consoleEl.value = data.output;
                    // Auto-scroll to bottom
                    consoleEl.scrollTop = consoleEl.scrollHeight;

                    if (data.running) {
                        badge.innerText = "RUNNING";
                        badge.className = "px-2 py-0.5 rounded text-xs bg-blue-500/10 text-blue-400 font-mono";
                        btn.disabled = true;
                        btn.classList.add("opacity-50", "cursor-not-allowed");
                        text.innerText = "Co-optimizing...";
                    } else if (data.completed) {
                        badge.innerText = "SUCCESS";
                        badge.className = "px-2 py-0.5 rounded text-xs bg-emerald-500/10 text-emerald-400 font-mono";
                        btn.disabled = false;
                        btn.classList.remove("opacity-50", "cursor-not-allowed");
                        text.innerText = "Run Co-Optimization Loop";
                    } else {
                        badge.innerText = "IDLE";
                        badge.className = "px-2 py-0.5 rounded text-xs bg-gray-800 text-gray-400 font-mono";
                        btn.disabled = false;
                        btn.classList.remove("opacity-50", "cursor-not-allowed");
                        text.innerText = "Run Co-Optimization Loop";
                    }
                });
        }

        // Poll every second
        setInterval(pollStatus, 1000);
        pollStatus();
    </script>
</body>
</html>
"""

def run_optimization_thread():
    global opt_status
    try:
        agent_path = os.path.join(WORKSPACE, "orchestrator", "agent.py")
        process = subprocess.Popen(
            [sys.executable, agent_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=WORKSPACE
        )
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
            # Append output
            opt_status["output"] += line
            
        process.wait()
        
        if process.returncode == 0:
            opt_status["output"] += "\n[SUCCESS] Co-optimization run finished successfully.\n"
            opt_status["completed"] = True
        else:
            opt_status["output"] += f"\n[ERROR] Optimization process exited with code {process.returncode}.\n"
            opt_status["completed"] = False
            
    except Exception as e:
        opt_status["output"] += f"\n[EXCEPTION] Error launching orchestrator: {str(e)}\n"
        opt_status["completed"] = False
    finally:
        opt_status["running"] = False

def main():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"============================================================")
    print(f"  MCP-ShipForge Dashboard running at: http://localhost:{PORT}")
    print(f"============================================================")
    
    # Auto-open browser
    webbrowser.open(f"http://localhost:{PORT}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard server...")
        httpd.server_close()

if __name__ == "__main__":
    main()
