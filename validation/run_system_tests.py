import os
import sys
import unittest
import numpy as np

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE not in sys.path:
    sys.path.append(WORKSPACE)

# Add server subdirectories to path
sys.path.append(os.path.join(WORKSPACE, "orchestrator"))
sys.path.append(os.path.join(WORKSPACE, "servers", "mcp_hull_cfd"))
sys.path.append(os.path.join(WORKSPACE, "servers", "mcp_material_db"))
sys.path.append(os.path.join(WORKSPACE, "servers", "mcp_rule_engine"))
sys.path.append(os.path.join(WORKSPACE, "servers", "mcp_structural_fea"))
sys.path.append(os.path.join(WORKSPACE, "servers", "mcp_fatigue_ml"))

# Import target functions
try:
    from surrogate_model import predict_fatigue_surrogate
    from sn_curves import get_fatigue_life
    from cfd_runner import run_resistance_cfd
    from dnv_part3_ch1 import calculate_design_pressure, check_plate_thickness_dnv
    from dnv_stability import check_intact_stability
    from fea_runner import calculate_section_properties, run_midship_stress_analysis
except ImportError as e:
    print(f"Error importing modules: {str(e)}")
    sys.exit(1)

class TestMCPFramework(unittest.TestCase):
    def test_dnv_pressure_and_plating(self):
        print("\n  [TEST 1] DNV Rule Plating scantlings calculations...")
        # Lpp=130m, Draft=6.8m, Beam=18.5m, Speed=14.5kn
        press_res = calculate_design_pressure("bottom", 130.0 * 0.95, 6.8, 18.5, 14.5, 6.0)
        self.assertIn("total_design_pressure_kPa", press_res)
        p_design = press_res["total_design_pressure_kPa"]
        self.assertGreater(p_design, 50.0) # Design pressure must be substantial
        
        # Test required plate thickness calculation
        thick_res = check_plate_thickness_dnv("bottom", "NV-AH36", p_design, 2.4, 0.8, 14.5, 1.5)
        self.assertIn("required_thickness_mm", thick_res)
        req_t = thick_res["required_thickness_mm"]
        self.assertGreater(req_t, 5.0) # Thickness must be positive
        print(f"    -> Design Pressure: {p_design:.2f} kPa, Required Thickness: {req_t:.2f} mm [PASS]")

    def test_intact_stability(self):
        print("\n  [TEST 2] DNV Intact stability metacentric check...")
        # Test baseline ship with loa=132.4m, beam=18.5m, draft=6.8m, Cb=0.75
        stab_res = check_intact_stability(132.4, 18.5, 6.8, 6.8 * 1.5, 0.75)
        self.assertIn("GM_over_LOA", stab_res)
        self.assertFalse(stab_res["passed"]) # Slender sequential baseline should fail stability
        print(f"    -> GM/L: {stab_res['GM_over_LOA']:.4f} (Required: >=0.033) [PASS]")

    def test_fea_girder_stress(self):
        print("\n  [TEST 3] Stiffened Box Girder FEA properties and hotspots...")
        # Beam=18.5m, Depth=10.2m, plate_t=25mm, spacing=2.4m
        section_props = calculate_section_properties(18.5, 10.2, 25.0, 2.4, 200.0, 10.0, 90.0, 12.0)
        self.assertGreater(section_props["moment_of_inertia_Iy_m4"], 0.0)
        self.assertGreater(section_props["section_modulus_bottom_m3"], 0.0)
        
        fea_res = run_midship_stress_analysis(
            section_props=section_props,
            material_yield_MPa=355.0,
            design_pressure_kPa=180.0,
            loa=132.4,
            beam=18.5,
            draft=6.8,
            Cb=0.75,
            sea_state_Hs=6.0
        )
        self.assertIn("combined_hotspot_stress_MPa", fea_res)
        print(f"    -> Hotspot Stress: {fea_res['combined_hotspot_stress_MPa']:.2f} MPa, Utilization: {fea_res['structural_utilization']:.3f} [PASS]")

    def test_fatigue_ml_surrogate(self):
        print("\n  [TEST 4] Fatigue ML surrogate model predictions...")
        res_air = predict_fatigue_surrogate(120.0, "NV-AH36", -1.0, "air")
        res_seawater = predict_fatigue_surrogate(120.0, "NV-AH36", -1.0, "seawater")
        self.assertGreater(res_air["log10_cycles_to_failure"], res_seawater["log10_cycles_to_failure"])
        print(f"    -> predicted air cycles: 10^{res_air['log10_cycles_to_failure']:.2f}, seawater cycles: 10^{res_seawater['log10_cycles_to_failure']:.2f} [PASS]")

if __name__ == "__main__":
    print("="*65)
    print("  MCP-ShipForge Proper System Verification & Tests Suite")
    print("="*65)
    unittest.main()
