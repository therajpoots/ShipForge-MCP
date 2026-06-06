"""
MCP-ShipForge: Local Co-Optimization Runner
=============================================
This is what the dashboard actually executes when you click "Run".

INPUT  (via CLI args or JSON):
  --loa_min / --loa_max  : LOA search range in metres (default 100-200)
  --speed                : Design speed in knots (default 14.5)
  --n_samples            : Number of Latin Hypercube designs to generate (default 20)
  --ship_type            : Hull type label (default bulk_carrier)
  --bow_type             : bulbous or conventional (default bulbous)

PIPELINE (7 steps per design):
  1. LHS sampling           → generate N hull parameter combinations
  2. Hull geometry (STL)    → generate_series60_hull() — analytical, not CAD software
  3. Resistance (kN)        → Holtrop-Mennen empirical formula (NOT OpenFOAM)
  4. DNV rule scantlings    → dnv_part3_ch1 pressure + plate thickness equations
  5. Structural analysis    → Beam theory (bending moment, I_y, section modulus, hotspot stress)
                              [Note: labelled FEA in diagram — this is analytical, not a FE solver]
  6. Fatigue life           → GBR ML surrogate trained on synthetic DNV-RP-C203 S-N data
  7. Intact stability       → GM/L metacentric height check (DNV criterion >= 0.033)

OUTPUT:
  - Pareto-optimal hull configuration (minimising drag, weight, fatigue damage simultaneously)
  - validation/plots/*.png (resistance, pareto, ablation, surrogate correlation)
  - results.json with best design summary
  - Printed summary to stdout (streamed to dashboard log console)

LLM STATUS: DeepSeek is NOT connected in this path.
The optimisation is purely numerical (LHS + Pareto front).
"""

import os
import sys
import json
import time
import argparse
import numpy as np

# ── Path setup ───────────────────────────────────────────────────────────────
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for subdir in ["orchestrator",
               "servers/mcp_hull_cfd",
               "servers/mcp_material_db",
               "servers/mcp_rule_engine",
               "servers/mcp_structural_fea",
               "servers/mcp_fatigue_ml"]:
    p = os.path.join(WORKSPACE, *subdir.split("/"))
    if p not in sys.path:
        sys.path.insert(0, p)

from surrogate_model import predict_fatigue_surrogate
from hull_generator import generate_series60_hull
from cfd_runner import run_resistance_cfd
from dnv_part3_ch1 import calculate_design_pressure, check_plate_thickness_dnv
from dnv_stability import check_intact_stability
from fea_runner import calculate_section_properties, run_midship_stress_analysis
from optimization import compute_pareto_front

PLOTS_DIR = os.path.join(WORKSPACE, "validation", "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)
LIVE_PATH = os.path.join(WORKSPACE, "validation", "live_designs.json")


def write_live_update(evaluated, total, params):
    """Write the current evaluation state to live_designs.json for dashboard polling."""
    cargo = [d for d in evaluated if d["stability"]["displacement_volume_m3"] >= 10000]
    try:
        pareto = compute_pareto_front(cargo) if len(cargo) >= 2 else cargo
    except Exception:
        pareto = []
    pareto_ids = {d["design_id"] for d in pareto}

    # Sequential baseline: picks the minimum drag design in the CARGO population (ignores stability)
    seq_baseline = min(cargo, key=lambda x: x["cfd"]["total_resistance_kN"]) if cargo else (
                   min(evaluated, key=lambda x: x["cfd"]["total_resistance_kN"]) if evaluated else None)

    # MCP best: must pass intact stability, FEA, and scantling rules in the cargo population
    feasible_cargo = [d for d in cargo if d["stability"]["passed"] and d["fea"]["passed"] and d["scantlings"]["passed"]]
    if feasible_cargo:
        try:
            pareto_feasible = compute_pareto_front(feasible_cargo)
            mcp_best = min(pareto_feasible, key=lambda x: x["cfd"]["total_resistance_kN"])
        except Exception:
            mcp_best = min(feasible_cargo, key=lambda x: x["cfd"]["total_resistance_kN"])
    else:
        # Fallback hierarchy: select best that passes stability, then FEA, then fallback to sequential baseline
        passing_stability = [d for d in cargo if d["stability"]["passed"]]
        if passing_stability:
            mcp_best = min(passing_stability, key=lambda x: x["cfd"]["total_resistance_kN"])
        else:
            mcp_best = seq_baseline

    # Best so far is the overall best cargo design in terms of resistance
    best = seq_baseline

    def design_entry(d):
        return {
            "id": d["design_id"],
            "hull": d["hull"],
            "resistance_kN": d["cfd"]["total_resistance_kN"],
            "frictional_kN": d["cfd"]["frictional_resistance_kN"],
            "wave_kN": d["cfd"]["wave_resistance_kN"],
            "froude": d["cfd"]["Froude_number"],
            "wetted_area_m2": d["cfd"]["wetted_surface_area_m2"],
            "weight_index": d["scantlings"]["actual_thickness_mm"] * 7.85,
            "plate_t_mm": d["scantlings"]["actual_thickness_mm"],
            "hotspot_MPa": d["fea"]["combined_hotspot_stress_MPa"],
            "utilization": d["fea"]["structural_utilization"],
            "gm_over_loa": d["stability"]["GM_over_LOA"],
            "displacement_m3": d["stability"]["displacement_volume_m3"],
            "fatigue_years": d["fatigue"]["cycles_to_failure"] / (1e8 / 25.0),
            "stability_pass": bool(d["stability"]["passed"]),
            "fea_pass": bool(d["fea"]["passed"]),
            "dnv_pass": bool(d["scantlings"]["passed"]),
            "pareto": d["design_id"] in pareto_ids,
        }

    live = {
        "total": total,
        "evaluated": len(evaluated),
        "designs": [design_entry(d) for d in evaluated],
        "best_so_far": design_entry(best) if best else None,
        "mcp_best": design_entry(mcp_best) if mcp_best else None,
        "seq_baseline": design_entry(seq_baseline) if seq_baseline else None,
        "params": {k: v for k, v in vars(params).items() if not k.startswith("_")},
    }
    try:
        with open(LIVE_PATH, "w") as f:
            json.dump(live, f)
    except Exception:
        pass


# ── LHS sampler (respects user-supplied LOA range) ───────────────────────────
def generate_lhs_samples_custom(n_samples, loa_min, loa_max, bow_type_pref="bulbous"):
    np.random.seed(None)  # random seed so each run differs
    grid = np.zeros((n_samples, 4))
    for i in range(4):
        bins = np.linspace(0.0, 1.0, n_samples + 1)
        pts = bins[:-1] + np.random.rand(n_samples) * (bins[1:] - bins[:-1])
        np.random.shuffle(pts)
        grid[:, i] = pts

    population = []
    for i in range(n_samples):
        loa = loa_min + grid[i, 0] * (loa_max - loa_min)
        lb_ratio = 5.5 + grid[i, 1] * 2.5
        beam = loa / lb_ratio
        bt_ratio = 2.2 + grid[i, 2] * 1.3
        draft = beam / bt_ratio
        Cb = 0.60 + grid[i, 3] * 0.22
        bow = bow_type_pref if i % 3 != 0 else ("conventional" if bow_type_pref == "bulbous" else "bulbous")
        population.append({
            "design_id": f"SF-{i+1:02d}",
            "hull": {
                "loa": round(float(loa), 1),
                "beam": round(float(beam), 1),
                "draft": round(float(draft), 1),
                "Cb": round(float(Cb), 2),
                "bow_type": bow
            }
        })
    return population


# ── Evaluate one design through the full pipeline ────────────────────────────
def evaluate_design(design: dict, speed_knots: float) -> dict:
    hull = design["hull"]
    loa, beam, draft, Cb, bow_type = (hull["loa"], hull["beam"],
                                       hull["draft"], hull["Cb"],
                                       hull["bow_type"])

    # Step 2 — Hull geometry (STL)
    mesh_path, _ = generate_series60_hull(loa, beam, draft, Cb, bow_type)

    # Step 3 — Resistance (Holtrop-Mennen empirical)
    cfd_res = run_resistance_cfd(mesh_path, speed_knots)

    # Step 4 — DNV design pressure + plate thickness
    pressure_res = calculate_design_pressure("bottom", loa * 0.95, draft, beam, speed_knots, 6.0)
    p_design = pressure_res["total_design_pressure_kPa"]
    req_thick_res = check_plate_thickness_dnv("bottom", "NV-AH36", p_design, 2.4, 0.8, 1.0, 1.5)
    req_t = req_thick_res["required_thickness_mm"]
    actual_t = float(np.ceil(req_t * 1.12))  # 12% safety margin
    scantling_res = check_plate_thickness_dnv("bottom", "NV-AH36", p_design, 2.4, 0.8, actual_t, 1.5)

    # Step 5 — Structural analysis (beam theory, NOT finite elements)
    section_props = calculate_section_properties(beam, draft * 1.5, actual_t, 2.4, 200.0, 10.0, 90.0, 12.0)
    fea_res = run_midship_stress_analysis(
        section_props=section_props,
        material_yield_MPa=355.0,
        design_pressure_kPa=p_design,
        loa=loa, beam=beam, draft=draft, Cb=Cb,
        sea_state_Hs=6.0
    )

    # Step 6 — Fatigue life (GBR ML surrogate)
    fatigue_res = predict_fatigue_surrogate(
        fea_res["combined_hotspot_stress_MPa"] * 0.18, "NV-AH36", -1.0, "seawater_cp"
    )
    cycles = fatigue_res["cycles_to_failure"]
    fatigue_res["cumulative_fatigue_damage"] = 1e7 / cycles if cycles > 0 else 9.9

    # Step 7 — Intact stability (GM/L check)
    stability_res = check_intact_stability(loa, beam, draft, draft * 1.5, Cb)

    return {
        "design_id": design["design_id"],
        "hull": hull,
        "cfd": cfd_res,
        "scantlings": scantling_res,
        "fea": fea_res,
        "fatigue": fatigue_res,
        "stability": stability_res,
        "p_design_kPa": p_design
    }


# -- Main ---------------------------------------------------------------------
def main():
    # Force UTF-8 output so special chars work in subprocess
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="MCP-ShipForge Local Optimiser")
    parser.add_argument("--loa_min",    type=float, default=100.0,   help="Min LOA (m)")
    parser.add_argument("--loa_max",    type=float, default=200.0,   help="Max LOA (m)")
    parser.add_argument("--speed",      type=float, default=14.5,    help="Design speed (knots)")
    parser.add_argument("--n_samples",  type=int,   default=20,      help="LHS sample count")
    parser.add_argument("--ship_type",  type=str,   default="bulk_carrier")
    parser.add_argument("--bow_type",   type=str,   default="bulbous",
                        choices=["bulbous", "conventional"])
    args = parser.parse_args()

    print("=" * 65)
    print("  MCP-ShipForge Local Co-Optimisation Pipeline")
    print("=" * 65)
    print(f"\n  INPUT BRIEF:")
    print(f"    Ship Type     : {args.ship_type}")
    print(f"    LOA Range     : {args.loa_min} - {args.loa_max} m")
    print(f"    Design Speed  : {args.speed} kn")
    print(f"    LHS Samples   : {args.n_samples}")
    print(f"    Bow Preference: {args.bow_type}")
    print()
    print("  PIPELINE STEPS:")
    print("    1  LHS Sampling          - generate hull parameter space")
    print("    2  Hull Geometry (STL)   - analytical Series-60 waterline formula")
    print("    3  Resistance (kN)       - Holtrop-Mennen (empirical, not CFD)")
    print("    4  DNV Scantlings        - Pt.3 Ch.1 pressure & plate thickness eqns")
    print("    5  Structural Analysis   - beam theory (I_y, Z, hotspot stress)")
    print("    6  Fatigue Life          - GBR ML surrogate (DNV-RP-C203 S-N data)")
    print("    7  Stability Check       - GM/L metacentric criterion (>= 0.033)")
    print()

    t0 = time.perf_counter()

    # Step 1: LHS
    print("-- Step 1: Generating LHS design population --")
    population = generate_lhs_samples_custom(args.n_samples, args.loa_min, args.loa_max, args.bow_type)
    print(f"  Generated {len(population)} design candidates\n")

    # Steps 2-7: Evaluate each design
    print("-- Steps 2-7: Evaluating designs --")
    evaluated = []
    # Clear live file
    try:
        with open(LIVE_PATH, "w") as f:
            json.dump({"total": len(population), "evaluated": 0, "designs": [], "best_so_far": None,
                       "mcp_best": None, "seq_baseline": None, "params": vars(args)}, f)
    except Exception:
        pass

    for i, design in enumerate(population):
        h = design["hull"]
        print(f"  [{i+1:02d}/{len(population)}] {design['design_id']}  "
              f"LOA={h['loa']}m  B={h['beam']}m  T={h['draft']}m  Cb={h['Cb']}  Bow={h['bow_type']}")
        try:
            result = evaluate_design(design, args.speed)
            cfd = result["cfd"]
            stab = result["stability"]
            fea = result["fea"]
            fat = result["fatigue"]
            print(f"         -> Resistance={cfd['total_resistance_kN']:.1f} kN  "
                  f"PlateT={result['scantlings']['actual_thickness_mm']:.1f} mm  "
                  f"Hotspot={fea['combined_hotspot_stress_MPa']:.1f} MPa  "
                  f"Stability={'PASS' if stab['passed'] else 'FAIL'}  "
                  f"FEA={'PASS' if fea['passed'] else 'FAIL'}")
            evaluated.append(result)
            write_live_update(evaluated, len(population), args)  # <- live streaming
        except Exception as e:
            print(f"         -> ERROR: {e}")

    elapsed = time.perf_counter() - t0
    print(f"\n  Evaluated {len(evaluated)}/{len(population)} designs in {elapsed:.2f}s")

    # Filter: must meet minimum displacement volume (commercial viability)
    cargo_designs = [d for d in evaluated
                     if d["stability"]["displacement_volume_m3"] >= 10000]
    print(f"  Displacement >= 10,000 m3 (cargo-viable): {len(cargo_designs)}")

    if len(cargo_designs) == 0:
        print("\n  [WARN] No designs passed cargo displacement constraint.")
        print("         Try increasing LOA_min or reducing LOA_max range.")
        sys.exit(1)

    # Pareto front
    pareto_front = compute_pareto_front(cargo_designs)
    print(f"  Pareto-optimal designs: {len(pareto_front)}")

    # Best design: least drag among Pareto-feasible designs that pass stability + FEA
    feasible = [d for d in cargo_designs if d["stability"]["passed"] and d["fea"]["passed"] and d["scantlings"]["passed"]]
    if feasible:
        try:
            pareto_feasible = compute_pareto_front(feasible)
            best = min(pareto_feasible, key=lambda x: x["cfd"]["total_resistance_kN"])
        except Exception:
            best = min(feasible, key=lambda x: x["cfd"]["total_resistance_kN"])
    else:
        passing_stability = [d for d in cargo_designs if d["stability"]["passed"]]
        if passing_stability:
            best = min(passing_stability, key=lambda x: x["cfd"]["total_resistance_kN"])
        else:
            best = min(cargo_designs, key=lambda x: x["cfd"]["total_resistance_kN"])

    # -- OUTPUT SUMMARY ------------------------------------------------------
    print("\n" + "=" * 65)
    print("  OPTIMAL DESIGN RESULT")
    print("=" * 65)
    bh = best["hull"]
    print(f"  Design ID        : {best['design_id']}")
    print(f"  LOA              : {bh['loa']} m")
    print(f"  Beam             : {bh['beam']} m")
    print(f"  Draft            : {bh['draft']} m")
    print(f"  Block Coeff (Cb) : {bh['Cb']}")
    print(f"  Bow Type         : {bh['bow_type']}")
    print(f"  Resistance       : {best['cfd']['total_resistance_kN']:.1f} kN")
    print(f"  Froude Number    : {best['cfd']['Froude_number']}")
    print(f"  Wetted Area      : {best['cfd']['wetted_surface_area_m2']:.1f} m²")
    print(f"  Plate Thickness  : {best['scantlings']['actual_thickness_mm']:.1f} mm")
    print(f"  Hotspot Stress   : {best['fea']['combined_hotspot_stress_MPa']:.1f} MPa")
    print(f"  Struct. Util.    : {best['fea']['structural_utilization']:.3f}  "
          f"({'OK' if best['fea']['passed'] else 'EXCEEDS 0.85'})")
    print(f"  GM/LOA           : {best['stability']['GM_over_LOA']:.4f}  "
          f"({'PASS' if best['stability']['passed'] else 'FAIL – below 0.033'})")
    print(f"  Disp. Volume     : {best['stability']['displacement_volume_m3']:.0f} m³")
    print(f"  Fatigue Life     : {best['fatigue']['cycles_to_failure'] / (1e8/25.0):.1f} yrs  "
          f"(log10 cycles = {best['fatigue']['log10_cycles_to_failure']:.2f})")
    print(f"  DNV Scantling    : {'PASS' if best['scantlings']['passed'] else 'FAIL'}")
    print(f"  Stability        : {'PASS' if best['stability']['passed'] else 'FAIL'}")

    # Save results JSON
    results_path = os.path.join(WORKSPACE, "validation", "results.json")
    with open(results_path, "w") as f:
        json.dump({
            "input": vars(args),
            "total_evaluated": len(evaluated),
            "cargo_viable": len(cargo_designs),
            "pareto_size": len(pareto_front),
            "best_design": {
                "id": best["design_id"],
                "hull": best["hull"],
                "resistance_kN": best["cfd"]["total_resistance_kN"],
                "froude_number": best["cfd"]["Froude_number"],
                "wetted_area_m2": best["cfd"]["wetted_surface_area_m2"],
                "plate_thickness_mm": best["scantlings"]["actual_thickness_mm"],
                "hotspot_stress_MPa": best["fea"]["combined_hotspot_stress_MPa"],
                "structural_utilization": best["fea"]["structural_utilization"],
                "fea_passed": best["fea"]["passed"],
                "gm_over_loa": best["stability"]["GM_over_LOA"],
                "stability_passed": best["stability"]["passed"],
                "displacement_volume_m3": best["stability"]["displacement_volume_m3"],
                "fatigue_life_years": best["fatigue"]["cycles_to_failure"] / (1e8/25.0),
                "dnv_scantling_passed": best["scantlings"]["passed"],
            },
            "all_pareto": [
                {
                    "id": d["design_id"],
                    "loa": d["hull"]["loa"],
                    "beam": d["hull"]["beam"],
                    "draft": d["hull"]["draft"],
                    "Cb": d["hull"]["Cb"],
                    "resistance_kN": d["cfd"]["total_resistance_kN"],
                    "plate_t_mm": d["scantlings"]["actual_thickness_mm"],
                    "stability_passed": d["stability"]["passed"],
                    "fea_passed": d["fea"]["passed"],
                }
                for d in pareto_front
            ]
        }, f, indent=2)
    print(f"\n  Results saved to: {results_path}")
    print("\n[DONE] Optimisation complete.")


if __name__ == "__main__":
    main()
