import numpy as np

def compute_corrosion_allowance(
    material_class: str,
    salinity_ppt: float = 35.0,
    temp_C: float = 15.0,
    exposure_years: float = 25.0,
    coating_quality: str = "good",
    cp_applied: bool = True
) -> dict:
    """
    Time-dependent corrosion model for shipbuilding materials in marine environments.
    Incorporates:
    - Melchers marine steel corrosion characteristics (salinity & temperature scaling).
    - Coating degradation delay (good/fair/poor/none).
    - Cathodic protection mitigation.
    """
    if material_class not in ["steel", "aluminium"]:
        # FRP / CFRP composites do not corrode in standard metallic terms (moisture absorption exists but mass loss is zero)
        return {
            "cumulative_corrosion_mm": 0.0,
            "corrosion_rate_mm_year": 0.0,
            "coating_delay_years": 0.0,
            "details": f"No metallic corrosion model applicable for {material_class}."
        }

    # Cathodic protection shuts down primary galvanic corrosion
    if cp_applied and material_class == "steel":
        rate = 0.005 # negligible background corrosion rate in mm/year under CP
        total_corrosion = rate * exposure_years
        return {
            "cumulative_corrosion_mm": round(total_corrosion, 4),
            "corrosion_rate_mm_year": rate,
            "coating_delay_years": 0.0,
            "details": "Cathodic protection active. Corrosion rate suppressed to background levels."
        }

    # Base corrosion rate parameters
    # Scaling factor based on standard seawater temperature (15 C) and salinity (35 ppt)
    salinity_factor = salinity_ppt / 35.0
    temp_factor = 1.0 + 0.03 * (temp_C - 15.0)
    
    if material_class == "steel":
        r_base = 0.09 * salinity_factor * temp_factor # base rate in mm/year
        power = 0.82 # Melchers power law coefficient for long-term corrosion limit
        coating_delays = {"good": 15.0, "fair": 8.0, "poor": 2.0, "none": 0.0}
    else: # aluminium (much higher corrosion resistance, pitting is localized, uniform rate is low)
        r_base = 0.015 * salinity_factor * temp_factor
        power = 0.65
        coating_delays = {"good": 10.0, "fair": 5.0, "poor": 1.0, "none": 0.0}

    delay = coating_delays.get(coating_quality.lower(), 0.0)
    t_effective = max(0.0, exposure_years - delay)

    if t_effective == 0.0:
        total_corrosion = 0.0
        current_rate = 0.0
    else:
        # Melchers formulation: c(t) = r_base * t^power
        total_corrosion = r_base * (t_effective ** power)
        current_rate = r_base * power * (t_effective ** (power - 1.0))

    return {
        "cumulative_corrosion_mm": round(total_corrosion, 4),
        "corrosion_rate_mm_year": round(current_rate, 4),
        "coating_delay_years": delay,
        "details": f"Corrosion based on power law model (base rate={r_base:.3f} mm/yr, power={power}). Coating delay of {delay} yrs applied."
    }
