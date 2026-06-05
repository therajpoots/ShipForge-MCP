import asyncio
import json
import os
import sys
import argparse
from mcp_client import MultiServerClient
from optimization import generate_lhs_samples, compute_pareto_front

# Add workspace to path
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE not in sys.path:
    sys.path.append(WORKSPACE)

class ShipForgeAgent:
    def __init__(self, use_llm: bool = False):
        self.client = MultiServerClient()
        self.use_llm = use_llm
        self.session_log = []
        
    async def initialize(self):
        await self.client.connect_all()
        
    async def run_tool(self, name: str, args: dict) -> dict:
        """
        Wrapper to run tool through MCP client and log it.
        """
        print(f"  [Tool Call] {name}({json.dumps(args)})")
        result = await self.client.call_tool(name, args)
        self.session_log.append({
            "tool": name,
            "inputs": args,
            "outputs": result
        })
        return result

    async def evaluate_design(self, design: dict) -> dict:
        """
        Executes the full multi-physics engineering workflow for a single design.
        This runs across multiple MCP servers.
        """
        hull = design["hull"]
        d_id = design["design_id"]
        
        # Step 1: Generate Mesh (CFD Server)
        mesh_info = await self.run_tool("generate_hull_mesh", {
            "loa": hull["loa"],
            "beam": hull["beam"],
            "draft": hull["draft"],
            "Cb": hull["Cb"],
            "bow_type": hull["bow_type"]
        })
        mesh_path = mesh_info["mesh_path"]
        
        # Step 2: Resistance simulation (CFD Server)
        cfd_res = await self.run_tool("run_resistance_simulation", {
            "mesh_path": mesh_path,
            "speed_knots": 14.5 # design speed
        })
        
        # Step 3: Design pressures (Rule Server)
        pressure_res = await self.run_tool("get_design_pressure", {
            "location": "bottom",
            "Lpp": hull["loa"] * 0.95,
            "draft": hull["draft"],
            "beam": hull["beam"],
            "speed_knots": 14.5
        })
        p_design = pressure_res["total_design_pressure_kPa"]
        
        # Step 4: Rule thickness checks (Rule Server)
        scantling_res = await self.run_tool("check_plate_thickness", {
            "location": "bottom",
            "material_id": "NV-AH36",
            "design_pressure_kPa": p_design,
            "plate_span_m": 2.4, # frame spacing
            "stiffener_spacing_m": 0.8,
            "actual_thickness_mm": 14.5 # baseline thickness
        })
        
        # Step 5: Build FEA Structural Model (FEA Server)
        model_res = await self.run_tool("build_midship_model", {
            "model_id": d_id,
            "frame_spacing": 2.4,
            "plate_t": scantling_res["required_thickness_mm"], # optimize plate thickness
            "stiffener_web_h_mm": 200.0,
            "stiffener_web_t_mm": 10.0,
            "stiffener_flange_w_mm": 90.0,
            "stiffener_flange_t_mm": 12.0,
            "material_id": "NV-AH36",
            "beam": hull["beam"],
            "depth": hull["draft"] * 1.5 # depth approx 1.5x draft
        })
        model_path = model_res["model_path"]
        
        # Step 6: Wave loads (FEA Server)
        load_res = await self.run_tool("apply_wave_loading", {
            "model_path": model_path,
            "sea_state": 6.0,
            "speed": 14.5,
            "draft": hull["draft"],
            "Cb": hull["Cb"]
        })
        load_file = load_res["load_file"]
        
        # Step 7: Static Bending Stress FEA (FEA Server)
        static_res = await self.run_tool("run_static_analysis", {
            "model_path": model_path,
            "load_file": load_file
        })
        hotspot_stress = static_res["combined_hotspot_stress_MPa"]
        
        # Step 8: Fatigue Damage evaluation (FEA Server / ML Server)
        # We can call either ML server or FEA server fatigue tool.
        # Let's call the ML surrogate model to represent surrogate capability!
        fatigue_res = await self.run_tool("predict_fatigue_life", {
            "stress_range": hotspot_stress * 0.6, # cyclic amplitude approx 60% of peak
            "material_id": "NV-AH36",
            "environment": "seawater_cp"
        })
        
        # Step 9: Stability check (Rule Server)
        stability_res = await self.run_tool("check_stability", {
            "loa": hull["loa"],
            "beam": hull["beam"],
            "draft": hull["draft"],
            "depth": hull["draft"] * 1.5,
            "Cb": hull["Cb"]
        })
        
        # Assemble design results
        evaluated_design = {
            "design_id": d_id,
            "hull": hull,
            "cfd": cfd_res,
            "scantlings": scantling_res,
            "fea": static_res,
            "fatigue": fatigue_res,
            "stability": stability_res
        }
        return evaluated_design

    async def optimize(self, design_brief: dict, max_iterations: int = 5):
        print("\n=== STARTING MCP-SHIPFORGE OPTIMIZATION LOOP ===")
        print(f"Design Brief: {json.dumps(design_brief, indent=2)}\n")
        
        # 1. LHS Initial Sampling
        print("Generating LHS initial population...")
        population = generate_lhs_samples(n_samples=10) # 10 designs for testing
        
        # 2. Evaluate Initial Population
        evaluated_population = []
        for idx, design in enumerate(population):
            print(f"\n--- Evaluating Design {idx+1}/{len(population)}: {design['design_id']} ---")
            try:
                eval_d = await self.evaluate_design(design)
                evaluated_population.append(eval_d)
            except Exception as e:
                print(f"Error evaluating design {design['design_id']}: {str(e)}")
                
        # 3. Compute Pareto Front
        pareto_front = compute_pareto_front(evaluated_population)
        print(f"\nOptimization completed. Initial population size: {len(evaluated_population)}")
        print(f"Pareto optimal designs found: {len(pareto_front)}")
        for d in pareto_front:
            print(f" - {d['design_id']}: Resistance = {d['cfd']['total_resistance_kN']:.1f} kN, Thickness = {d['scantlings']['required_thickness_mm']:.1f} mm, Fatigue = {d['fatigue']['cycles_to_failure']:.1e} cycles")
            
        # 4. Generate report for the best Pareto design (minimize resistance)
        if pareto_front:
            best_design = min(pareto_front, key=lambda x: x["cfd"]["total_resistance_kN"])
            print(f"\nGenerating design package for best hydrodynamic design: {best_design['design_id']}")
            
            # PDF Report
            report_res = await self.run_tool("generate_design_report", {
                "design_id": best_design["design_id"],
                "design_data": best_design,
                "population": evaluated_population
            })
            print(f"PDF design report generated: {report_res['report_pdf_path']}")
            
            # IGES Export
            iges_res = await self.run_tool("export_to_iges", {
                "hull_mesh_path": best_design["cfd"]["simulation_mode"].split("'")[-2] if "stl" in best_design["cfd"]["simulation_mode"] else os.path.join(WORKSPACE, "servers", "mcp_hull_cfd", "meshes", f"hull_loa{best_design['hull']['loa']:.1f}_b{best_design['hull']['beam']:.1f}_d{best_design['hull']['draft']:.1f}_cb{best_design['hull']['Cb']:.2f}_bulbous.stl")
            })
            print(f"IGES geometry file generated: {iges_res['iges_file_path']}")
            
            # Session Audit Log
            audit_res = await self.run_tool("export_audit_log", {
                "session_id": "session_opt_01",
                "session_log": self.session_log
            })
            print(f"Audit log JSON generated: {audit_res['audit_log_path']}")
            
        # Cleanup
        await self.client.close()

async def main():
    parser = argparse.ArgumentParser(description="MCP-ShipForge Orchestrator Agent")
    parser.add_argument("--brief", help="Path to design brief JSON", default=None)
    args = parser.parse_args()
    
    brief = {
        "ship_type": "bulk_carrier",
        "loa_target": 150.0,
        "design_speed_knots": 14.5,
        "material_class": "steel"
    }
    
    if args.brief and os.path.exists(args.brief):
        with open(args.brief, "r") as f:
            brief = json.load(f)
            
    agent = ShipForgeAgent()
    await agent.initialize()
    await agent.optimize(brief)

if __name__ == "__main__":
    asyncio.run(main())
