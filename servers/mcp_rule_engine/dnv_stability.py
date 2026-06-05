import numpy as np

def check_intact_stability(
    loa: float,
    beam: float,
    draft: float,
    depth: float,
    Cb: float,
    kg_m: float = None
) -> dict:
    """
    Evaluates ship intact stability using transverse metacentric height (GM) approximation.
    Verifies DNV compliance constraint: GM / LOA > 0.033.
    """
    # 1. Estimate Vertical Center of Buoyancy (KB)
    # Morrish's formula / standard approximation: KB = T * (5/6 - 1/3 * Cb/Cwp)
    # Or simplified: KB approx 0.54 * draft
    Cwp = 0.7 * Cb + 0.3 # Waterplane area coefficient approximation
    kb = draft * (5.0 / 6.0 - 0.333 * Cb / Cwp)
    
    # 2. Estimate Transverse Metacentric Radius (BM)
    # BM = I_T / Delta
    # I_T = C_it * L * B^3 / 12 (transverse inertia coefficient C_it approx 0.04 to 0.06 depending on Cwp)
    # Standard approximation for waterplane inertia factor:
    C_it = (1.0 + 2.0 * Cwp) ** 2 / 12.0 * 0.09 # simplified waterplane coefficient scaling
    C_it = 0.04 + 0.05 * Cwp # regression form
    
    I_T = C_it * loa * (beam ** 3)
    displacement_vol = Cb * loa * beam * draft
    bm = I_T / displacement_vol if displacement_vol > 0 else 0.0
    
    # 3. Transverse Metacenter height above keel (KM)
    km = kb + bm
    
    # 4. Vertical Center of Gravity (KG)
    # If not provided, assume KG is 62% of depth (representative for cargo ships)
    if kg_m is None:
        kg = 0.62 * depth
    else:
        kg = kg_m
        
    # Metacentric Height (GM)
    gm = km - kg
    
    gm_over_loa = gm / loa if loa > 0 else 0.0
    passed = gm_over_loa >= 0.033
    
    return {
        "displacement_volume_m3": round(displacement_vol, 2),
        "KB_m": round(kb, 2),
        "BM_m": round(bm, 2),
        "KM_m": round(km, 2),
        "KG_m": round(kg, 2),
        "GM_m": round(gm, 2),
        "GM_over_LOA": round(gm_over_loa, 4),
        "passed": bool(passed),
        "rule_reference": "DNV-GL Intact Stability Code Part A (GM/L >= 0.033)"
    }
