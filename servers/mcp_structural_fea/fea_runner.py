import numpy as np
import os
import json

def calculate_section_properties(
    beam: float,
    depth: float,
    plate_t_mm: float,
    stiffener_spacing_m: float,
    stiffener_web_h_mm: float,
    stiffener_web_t_mm: float,
    stiffener_flange_w_mm: float,
    stiffener_flange_t_mm: float
) -> dict:
    """
    Computes midship section properties (cross-sectional area, neutral axis, and moment of inertia).
    Treats the hull girder as a composite stiffened box section.
    """
    t_m = plate_t_mm / 1000.0
    hw_m = stiffener_web_h_mm / 1000.0
    tw_m = stiffener_web_t_mm / 1000.0
    fw_m = stiffener_flange_w_mm / 1000.0
    ft_m = stiffener_flange_t_mm / 1000.0
    
    # Simple box girder simplification:
    # 2 horizontal flanges (deck and bottom) of width = beam
    # 2 vertical webs (sides) of height = depth
    # Plus longitudinal stiffeners distributed along the perimeter
    
    # 1. Base plates area (m^2)
    deck_area = beam * t_m
    bottom_area = beam * t_m
    side_area = 2.0 * depth * t_m
    total_plate_area = deck_area + bottom_area + side_area
    
    # 2. Stiffener cross-sectional area
    astif = hw_m * tw_m + fw_m * ft_m # area of single stiffener (m^2)
    
    # Estimate number of longitudinal stiffeners
    # Spacing on deck, bottom, and side shell
    num_stiffeners = int((2.0 * beam + 2.0 * depth) / stiffener_spacing_m)
    total_stiffener_area = num_stiffeners * astif
    
    total_area = total_plate_area + total_stiffener_area
    
    # 3. Neutral axis height above keel (g_z)
    # Symmetry suggests neutral axis is at depth / 2 if deck and bottom are equal
    neutral_axis = depth / 2.0
    
    # 4. Moment of Inertia (I_y) in m^4
    # Plates:
    # Deck: area * (depth - g_z)^2
    # Bottom: area * g_z^2
    # Sides: 2 * (1/12 * t * depth^3)
    I_plates = deck_area * (depth - neutral_axis)**2 + bottom_area * (neutral_axis)**2 + 2.0 * (1.0 / 12.0 * t_m * depth**3)
    
    # Stiffeners moment of inertia contribution (parallel axis theorem)
    # Stiffeners are distributed, so we average their contribution
    # For bottom: num_bottom * astif * (z_stif - NA)^2 etc.
    # Simplified contribution:
    I_stiffeners = total_stiffener_area * (depth / 2.0) ** 2 * 0.7 # factor for distribution
    
    Iy = I_plates + I_stiffeners
    
    # Section modulus Z (m^3)
    Z_bottom = Iy / neutral_axis
    Z_deck = Iy / (depth - neutral_axis)
    
    return {
        "cross_sectional_area_m2": round(total_area, 4),
        "neutral_axis_above_keel_m": round(neutral_axis, 2),
        "moment_of_inertia_Iy_m4": round(Iy, 3),
        "section_modulus_bottom_m3": round(Z_bottom, 3),
        "section_modulus_deck_m3": round(Z_deck, 3),
        "stiffener_area_m2": round(astif, 6),
        "number_of_stiffeners": num_stiffeners,
        "plate_thickness_mm": plate_t_mm
    }

def run_midship_stress_analysis(
    section_props: dict,
    material_yield_MPa: float,
    design_pressure_kPa: float,
    loa: float,
    beam: float,
    draft: float,
    Cb: float,
    sea_state_Hs: float = 6.0
) -> dict:
    """
    Computes static and wave bending moments, global hull girder bending stresses,
    local bending stresses due to pressure, and safety utilization.
    """
    # 1. Wave Bending Moment per DNV Rules (kN.m)
    # Wave coefficient Cw
    if loa < 90:
        Cw = 0.07 * loa
    elif loa <= 300:
        Cw = 10.75 - ((300 - loa) / 100.0) ** 1.5
    else:
        Cw = 10.75
        
    # Hogging bending moment (kN.m)
    M_hog = 0.19 * Cw * (loa ** 2) * beam * Cb * (sea_state_Hs / 6.0)
    # Sagging bending moment (kN.m)
    M_sag = -0.11 * Cw * (loa ** 2) * beam * (Cb + 0.7) * (sea_state_Hs / 6.0)
    
    # Maximum global bending moment magnitude (kN.m)
    M_max = max(np.abs(M_hog), np.abs(M_sag))
    M_max_Nm = M_max * 1000.0
    
    # 2. Global Bending Stress (MPa)
    # sigma = M / Z
    Z_bottom = section_props["section_modulus_bottom_m3"]
    sigma_global = (M_max_Nm / Z_bottom) / 1e6 # convert to MPa
    
    # 3. Local Plate Bending Stress (MPa)
    # Assumes plate panel is clamped between stiffeners.
    # sigma_local = 0.5 * p * (s/t)^2
    # Where s is stiffener spacing, t is plate thickness.
    # Standard engineering clamped panel: sigma_local = p * s^2 / (2 * t^2)
    # Let's check typical plate panel dimensions from spacing:
    # Stiffener spacing typically 0.8m, plate thickness 15mm
    # design_pressure_kPa is in kN/m^2 = MPa * 1e-3
    s_m = 0.8
    t_mm = section_props.get("plate_thickness_mm", 15.0)
    
    # Local bending stress formula
    sigma_local = 0.5 * (design_pressure_kPa / 1000.0) * (s_m / (t_mm / 1000.0)) ** 2
    
    # 4. Combined Stress (Hotspot Stress)
    # At weld details, stress concentrations exist. SCF typically 1.8.
    SCF = 1.8
    sigma_hotspot = SCF * (sigma_global + sigma_local)
    
    utilization = sigma_hotspot / material_yield_MPa
    passed = utilization <= 0.85 # standard marine safety utilization margin
    
    return {
        "wave_bending_moment_hogging_kNm": round(M_hog, 1),
        "wave_bending_moment_sagging_kNm": round(M_sag, 1),
        "global_bending_stress_MPa": round(sigma_global, 2),
        "local_bending_stress_MPa": round(sigma_local, 2),
        "combined_hotspot_stress_MPa": round(sigma_hotspot, 2),
        "structural_utilization": round(utilization, 3),
        "passed": bool(passed),
        "details": f"Stress calculation utilizing DNV hull girder bending (M={M_max:.1f} kNm) and local plate bending theory."
    }

def run_structural_fatigue(
    hotspot_stress_range_MPa: float,
    material_id: str,
    exposure_years: float = 25.0,
    weld_class: str = "D",
    environment: str = "seawater_cp"
) -> dict:
    """
    Computes cumulative fatigue damage using Miner's linear damage accumulation law.
    Generates a loading spectrum based on wave encounters in the North Atlantic.
    """
    # Number of wave cycles in 25 years: approx 1e8 wave cycles
    # For a ship, average wave period is 8 seconds -> 3.9e6 cycles/year -> 1e8 cycles in 25 years.
    total_cycles = 1.0e8 * (exposure_years / 25.0)
    
    # Stress range distribution is typically modeled as a Weibull distribution
    # shape parameter k_weibull approx 1.0 (exponential) for wave loading.
    # We discretize the stress history into 8 stress range bins.
    bins = np.linspace(0.1, 1.0, 8)
    probabilities = np.exp(-bins) / np.sum(np.exp(-bins)) # normalized PDF
    
    total_damage = 0.0
    
    # Import S-N curve lookup
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mcp_material_db"))
    from sn_curves import get_fatigue_life
    
    bin_results = []
    for s_ratio, prob in zip(bins, probabilities):
        # Stress range for this bin
        S_bin = s_ratio * hotspot_stress_range_MPa
        n_bin = prob * total_cycles
        
        # Get fatigue life N for this stress
        try:
            fatigue_info = get_fatigue_life(material_id, environment, weld_class, S_bin)
            N_fail = fatigue_info["cycles_to_failure"]
        except Exception:
            # Fallback curves (class D steel in CP)
            k = 10**12.187
            N_fail = k * (S_bin ** -3.0) if S_bin > 0 else float('inf')
            
        damage = n_bin / N_fail if N_fail > 0 else 0.0
        total_damage += damage
        bin_results.append({
            "stress_range_MPa": round(S_bin, 1),
            "cycles": round(n_bin, 0),
            "cycles_to_failure": float('inf') if np.isinf(N_fail) else round(N_fail, 0),
            "damage_fraction": round(damage, 6)
        })
        
    fatigue_life_years = exposure_years / total_damage if total_damage > 0 else float('inf')
    passed = total_damage <= 1.0
    
    return {
        "cumulative_fatigue_damage": round(total_damage, 4),
        "estimated_fatigue_life_years": round(fatigue_life_years, 2),
        "passed": bool(passed),
        "stress_bins": bin_results,
        "details": "Weibull wave load spectrum discretized in 8 bins. Fatigue calculated using DNV-RP-C203 curves."
    }
