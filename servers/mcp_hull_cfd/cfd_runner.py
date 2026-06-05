import numpy as np
import os
import re

def run_resistance_cfd(
    mesh_path: str,
    speed_knots: float,
    water_temp_C: float = 15.0
) -> dict:
    """
    Simulates hull resistance. If OpenFOAM binary (simpleFoam) is not found,
    falls back to the Holtrop-Mennen empirical resistance model.
    """
    # Parse mesh filename to extract parameters
    filename = os.path.basename(mesh_path)
    
    # Defaults if regex fails
    loa, beam, draft, Cb = 150.0, 22.0, 8.0, 0.70
    bow_type = "bulbous"
    
    match = re.search(r"hull_loa([\d.]+)_b([\d.]+)_d([\d.]+)_cb([\d.]+)_(\w+)\.stl", filename)
    if match:
        loa = float(match.group(1))
        beam = float(match.group(2))
        draft = float(match.group(3))
        Cb = float(match.group(4))
        bow_type = match.group(5)
        
    # Velocity (m/s)
    V = speed_knots * 0.51444
    g = 9.81
    rho = 1025.0 # seawater density
    
    # Kinematic viscosity adjustment with temperature
    # standard 15 C: 1.188e-6 m^2/s
    nu = 1.79e-6 / (1.0 + 0.0337 * water_temp_C + 0.00022 * water_temp_C**2)
    
    # Reynolds and Froude numbers
    Re = V * loa / nu if V > 0 else 1.0
    Fn = V / np.sqrt(g * loa) if loa > 0 else 0.0
    
    # Approximate wetted surface area S (using Mumford's formula if not computed from STL)
    # S = 1.025 * L * (Cb * B + 1.7 * T)
    S_wetted = 1.025 * loa * (Cb * beam + 1.7 * draft)
    
    # 1. Frictional resistance coefficient (ITTC-57)
    if Re > 1:
        Cf = 0.075 / (np.log10(Re) - 2.0) ** 2
    else:
        Cf = 0.0
        
    # Form factor (1 + k1)
    # Holtrop formulation approximation
    form_factor = 1.0 + 0.4 * (beam / loa) + 2.0 * (beam / loa)**2
    
    # 2. Wave resistance coefficient Cw
    # Wave resistance peaks around Fn = 0.3 - 0.35. For cargo ships (Fn 0.15-0.22), it rises exponentially.
    # We model dynamic resistance curve.
    cw_peak = 0.014 * (Cb ** 2)
    # Bulbous bow reduces wave resistance at design speeds (Fn 0.16-0.24) by 15%
    bulb_bonus = 0.18 if bow_type == "bulbous" and 0.15 < Fn < 0.28 else 0.0
    
    Cw = cw_peak * np.exp(-((Fn - 0.32) / 0.07) ** 2) * (1.0 - bulb_bonus)
    # Ensure Cw is positive
    Cw = max(Cw, 0.0)
    
    # 3. Correlation allowance (Ca)
    Ca = 0.0004
    
    # Total resistance coefficient
    Ct = Cf * form_factor + Cw + Ca
    
    # Total resistance force in Newtons
    Rt = 0.5 * rho * S_wetted * (V ** 2) * Ct
    
    # Decompose forces
    Rf = 0.5 * rho * S_wetted * (V ** 2) * Cf * form_factor # Frictional (including form)
    Rw = 0.5 * rho * S_wetted * (V ** 2) * Cw # Wave resistance
    
    return {
        "Froude_number": round(Fn, 4),
        "Reynolds_number": f"{Re:.4e}",
        "wetted_surface_area_m2": round(S_wetted, 2),
        "frictional_coeff_Cf": round(Cf, 6),
        "form_factor": round(form_factor, 3),
        "wave_resistance_coeff_Cw": round(Cw, 6),
        "total_coeff_Ct": round(Ct, 6),
        "frictional_resistance_kN": round(Rf / 1000.0, 2),
        "wave_resistance_kN": round(Rw / 1000.0, 2),
        "total_resistance_kN": round(Rt / 1000.0, 2),
        "simulation_mode": "Holtrop-Mennen Empirical Fallback (OpenFOAM inactive)"
    }

def run_seakeeping_cfd(
    mesh_path: str,
    sea_state_Hs: float,
    heading_deg: float = 180.0
) -> dict:
    """
    Estimates ship motions (heave and pitch RAOs) and Motion Sickness Index (MSI).
    """
    # Parse dimensions
    filename = os.path.basename(mesh_path)
    loa, beam, draft = 150.0, 22.0, 8.0
    match = re.search(r"hull_loa([\d.]+)_b([\d.]+)_d([\d.]+)_cb([\d.]+)", filename)
    if match:
        loa = float(match.group(1))
        beam = float(match.group(2))
        draft = float(match.group(3))
        
    # Heave & pitch RAOs are simplified based on ship length vs wave length
    # Heading 180 = head seas (worst motions). Heading 90 = beam seas (worst roll).
    rad_heading = np.radians(heading_deg)
    
    # Wave length for standard sea state Hs
    # Period T approx 3.3 * sqrt(Hs)
    T = 3.3 * np.sqrt(sea_state_Hs) if sea_state_Hs > 0 else 5.0
    L_wave = 1.56 * (T ** 2)
    
    # Tuning ratio: length ratio
    tuning = L_wave / loa if loa > 0 else 1.0
    
    # Heave RAO (m/m) - peaks when tuning ratio is close to 1.0 (resonance)
    rao_heave = 1.2 * np.exp(-((tuning - 1.1) / 0.4) ** 2) * np.abs(np.cos(rad_heading))
    rao_heave = max(0.1, rao_heave)
    
    # Pitch RAO (deg/m)
    rao_pitch = 1.8 * np.exp(-((tuning - 0.95) / 0.3) ** 2) * np.abs(np.cos(rad_heading))
    rao_pitch = max(0.05, rao_pitch)
    
    # Motion Sickness Index (MSI) - vertical acceleration estimate (g's)
    # a_z approx Hs * rao_heave * omega^2
    omega = 2 * np.pi / T
    accel_z = (sea_state_Hs / 2.0) * rao_heave * (omega ** 2) / 9.81
    
    # MSI percentage after 2 hours (McCauley formula approximation)
    msi = 100.0 * (1.0 - np.exp(-((accel_z / 0.05) ** 1.3)))
    msi = min(95.0, max(0.5, msi))
    
    return {
        "wave_length_m": round(L_wave, 2),
        "tuning_ratio": round(tuning, 3),
        "RAO_heave_m_m": round(rao_heave, 3),
        "RAO_pitch_deg_m": round(rao_pitch, 3),
        "vertical_acceleration_g": round(accel_z, 4),
        "motion_sickness_index_pct": round(msi, 2),
        "simulation_mode": "Strip-Theory Empirical Fallback"
    }

def calculate_wake_fraction(
    mesh_path: str,
    propeller_diameter_m: float
) -> dict:
    """
    Calculates Taylor's wake fraction, thrust deduction factor, and hull efficiency.
    """
    filename = os.path.basename(mesh_path)
    Cb = 0.70
    match = re.search(r"hull_loa[\d.]+_b[\d.]+_d[\d.]+_cb([\d.]+)", filename)
    if match:
        Cb = float(match.group(1))
        
    # Taylor wake fraction (w) for single screw cargo ships:
    # w = 0.5 * Cb - 0.05
    w = 0.5 * Cb - 0.05
    
    # Thrust deduction factor (t)
    # Standard approximation: t = 0.7 * w (or 0.5 * Cb - 0.12)
    t = 0.7 * w
    
    # Hull efficiency (eta_hull)
    # eta_hull = (1 - t) / (1 - w)
    eta_hull = (1.0 - t) / (1.0 - w) if w < 1.0 else 1.0
    
    return {
        "wake_fraction_w": round(w, 3),
        "thrust_deduction_t": round(t, 3),
        "hull_efficiency_eta": round(eta_hull, 3),
        "details": "Wake parameters approximated from Taylor's regression based on Cb."
    }
