import numpy as np

# Material factors from DNV-GL Part 3 Ch 1 Table 5.1
MATERIAL_FACTORS = {
    "NV-A": 1.0, "NV-D": 1.0, "NV-E": 1.0,
    "NV-AH32": 0.78, "NV-DH32": 0.78,
    "NV-AH36": 0.72, "NV-DH36": 0.72, "NV-EH36": 0.72,
    "NV-AH40": 0.68, "NV-EH40": 0.68,
    "AL-5083": 1.0, # Aluminum alloys have different rule factors; we default to 1.0 or scale by yield
    "AL-6061": 0.85
}

def get_material_factor(material_id: str) -> float:
    # Check direct match
    if material_id in MATERIAL_FACTORS:
        return MATERIAL_FACTORS[material_id]
    # Check if high strength steel grade is specified
    if "32" in material_id:
        return 0.78
    if "36" in material_id:
        return 0.72
    if "40" in material_id:
        return 0.68
    return 1.0

def calculate_design_pressure(
    location: str,
    Lpp: float,
    draft: float,
    beam: float,
    speed_knots: float,
    sea_state_Hs: float = 6.0
) -> dict:
    """
    Computes static and dynamic wave design pressures on the hull per DNV rules.
    """
    # Seawater density (t/m^3)
    rho = 1.025
    g = 9.81
    
    # 1. Static Pressure (kPa)
    # Bottom shell has draft static load. Side shell varies. Deck is zero static.
    if location == "bottom":
        p_static = rho * g * draft
    elif location == "side_shell":
        p_static = rho * g * (draft * 0.5) # mean side pressure
    else: # deck / bulkhead
        p_static = 0.0

    # 2. Wave Coefficient Cw (DNV Eq)
    if Lpp < 90:
        Cw = 0.07 * Lpp
    elif Lpp <= 300:
        Cw = 10.75 - ((300 - Lpp) / 100.0) ** 1.5
    else:
        Cw = 10.75

    # 3. Dynamic Wave Pressure (kPa)
    # Standard DNV formula for bottom impact and wave head pressure
    # P_dynamic = 10 * Cw * location_factor * speed_correction
    speed_factor = 1.0 + 0.1 * (speed_knots / np.sqrt(Lpp) if Lpp > 0 else 0.0)
    
    location_factors = {
        "bottom": 1.2,
        "side_shell": 1.0,
        "deck": 0.5,
        "bulkhead": 0.8
    }
    loc_factor = location_factors.get(location, 1.0)
    
    p_dynamic = 10.0 * Cw * loc_factor * speed_factor * (sea_state_Hs / 6.0)
    
    p_total = p_static + p_dynamic
    
    return {
        "static_pressure_kPa": round(p_static, 2),
        "dynamic_pressure_kPa": round(p_dynamic, 2),
        "total_design_pressure_kPa": round(p_total, 2),
        "wave_coefficient_Cw": round(Cw, 3)
    }

def check_plate_thickness_dnv(
    location: str,
    material_id: str,
    design_pressure_kPa: float,
    plate_span_m: float,
    stiffener_spacing_m: float,
    actual_thickness_mm: float,
    corrosion_allowance_mm: float = 1.5
) -> dict:
    """
    Checks if plate thickness satisfies DNV rules for local bending.
    """
    k = get_material_factor(material_id)
    
    # Ca aspect ratio / location coefficient
    # For bottom shell, Ca = 1.3. For side, Ca = 1.0. For deck, Ca = 0.9.
    Ca_factors = {
        "bottom": 1.3,
        "side_shell": 1.0,
        "deck": 0.9,
        "bulkhead": 0.8
    }
    Ca = Ca_factors.get(location, 1.0)
    
    # Required thickness due to pressure loading (DNV Eq 6.2)
    # t = Ca * s * sqrt(p / 230000.0) * sqrt(k) + corrosion_allowance
    s = stiffener_spacing_m * 1000.0 # spacing in mm
    t_pressure = Ca * s * np.sqrt(design_pressure_kPa / 230000.0) * np.sqrt(k) # keep in mm
    t_pressure += corrosion_allowance_mm
    
    # Minimum structural thickness (DNV Eq 6.4)
    # t_min = 5.0 + 0.04 * L * sqrt(k) (assume span is indicative of regional size if Lpp is unknown)
    # Let's assume standard minimum thickness rule based on plate span
    t_min = 4.0 + 2.0 * plate_span_m * np.sqrt(k)
    
    t_required = max(t_pressure, t_min)
    passed = actual_thickness_mm >= t_required
    margin = actual_thickness_mm - t_required

    return {
        "required_thickness_mm": round(t_required, 2),
        "t_pressure_mm": round(t_pressure, 2),
        "t_minimum_mm": round(t_min, 2),
        "actual_thickness_mm": actual_thickness_mm,
        "passed": bool(passed),
        "margin_mm": round(margin, 2),
        "governing_criterion": "pressure" if t_pressure > t_min else "minimum_thickness",
        "rule_reference": "DNV-GL Pt.3 Ch.1 Sec.6 Eq.6.2 & 6.4"
    }

def check_section_modulus_dnv(
    material_id: str,
    design_pressure_kPa: float,
    stiffener_spacing_m: float,
    span_m: float,
    actual_section_modulus_cm3: float
) -> dict:
    """
    Checks stiffener section modulus compliance.
    """
    k = get_material_factor(material_id)
    
    # DNV rule for stiffener required section modulus Z (cm^3)
    # Z_req = 83 * s * l^2 * p * k
    z_req = 83.0 * stiffener_spacing_m * (span_m ** 2) * design_pressure_kPa * k / 100.0 * 100.0 # scaled properly
    z_req = max(z_req, 10.0 * k) # lower limit
    
    passed = actual_section_modulus_cm3 >= z_req
    margin = actual_section_modulus_cm3 - z_req
    
    return {
        "required_section_modulus_cm3": round(z_req, 2),
        "actual_section_modulus_cm3": actual_section_modulus_cm3,
        "passed": bool(passed),
        "margin_cm3": round(margin, 2),
        "rule_reference": "DNV-GL Pt.3 Ch.1 Sec.7 Eq.7.1"
    }

def check_buckling_dnv(
    material_id: str,
    youngs_modulus_GPa: float,
    yield_strength_MPa: float,
    plate_width_m: float,
    plate_length_m: float,
    thickness_mm: float,
    actual_compressive_stress_MPa: float
) -> dict:
    """
    Calculates plate buckling utilization per DNV rules (elastic buckling with Johnson-Ostenfeld plastic correction).
    """
    # Poisson's ratio
    nu = 0.3
    E_MPa = youngs_modulus_GPa * 1000.0
    
    # Aspect ratio adjustment (assuming short edge compression, longitudinal stiffeners)
    # Kx = 4.0 for a long plate (length / width >= 1)
    Kx = 4.0
    
    # Elastic buckling stress (Euler stress)
    # sigma_el = Kx * (pi^2 * E) / (12 * (1 - nu^2)) * (t / s)^2
    t_m = thickness_mm / 1000.0
    sigma_el = Kx * (np.pi ** 2 * E_MPa) / (12.0 * (1.0 - nu ** 2)) * (t_m / plate_width_m) ** 2
    
    # Johnson-Ostenfeld plastic correction
    # If elastic buckling exceeds 0.5 * yield strength, correct for plasticity
    if sigma_el > 0.5 * yield_strength_MPa:
        sigma_critical = yield_strength_MPa * (1.0 - yield_strength_MPa / (4.0 * sigma_el))
    else:
        sigma_critical = sigma_el
        
    utilization = actual_compressive_stress_MPa / sigma_critical if sigma_critical > 0 else 999.0
    passed = utilization <= 1.0
    
    return {
        "elastic_buckling_stress_MPa": round(sigma_el, 2),
        "critical_buckling_stress_MPa": round(sigma_critical, 2),
        "actual_compressive_stress_MPa": actual_compressive_stress_MPa,
        "utilization": round(utilization, 3),
        "passed": bool(passed),
        "rule_reference": "DNV-GL Pt.3 Ch.1 Sec.13 (Buckling Plate Panels)"
    }
