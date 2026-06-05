import sqlite3
import os
import numpy as np

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "materials.db")

def get_fatigue_life(
    material_id: str,
    environment: str,
    weld_class: str,
    stress_range_MPa: float
) -> dict:
    """
    Computes fatigue life (cycles to failure N) for a given stress range,
    using DNV-RP-C203 double-slope S-N curve coefficients retrieved from SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query curve parameters
    cursor.execute("""
        SELECT log_k1, m1, log_k2, m2, transition_n, standard 
        FROM sn_curves 
        WHERE material_id = ? AND environment = ? AND weld_class = ?
    """, (material_id, environment, weld_class))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        # Fallback to general steel class D if exact match fails
        # (Allows soft matches for different steel grades, since weld detail geometry governs)
        if "NV-" in material_id:
            return get_fatigue_life("NV-A", environment, weld_class, stress_range_MPa)
        raise ValueError(f"S-N curve parameters not found for {material_id}, {environment}, {weld_class}")
        
    log_k1, m1, log_k2, m2, transition_n, standard = row
    
    # Calculate transition stress range S_transition
    # N = k1 * S^(-m1) => S = (k1 / N)^(1/m1)
    k1 = 10**log_k1
    s_transition = (k1 / transition_n) ** (1.0 / m1)
    
    if stress_range_MPa >= s_transition:
        m_active = m1
        log_k_active = log_k1
        segment = "high stress (segment 1)"
    else:
        m_active = m2
        log_k_active = log_k2
        segment = "low stress (segment 2)"
        
    k_active = 10**log_k_active
    
    # Calculate fatigue life N
    # Avoid division by zero
    if stress_range_MPa <= 0:
        N = float('inf')
    else:
        N = k_active * (stress_range_MPa ** (-m_active))
        
    return {
        "cycles_to_failure": N,
        "active_exponent_m": m_active,
        "active_log_k": log_k_active,
        "transition_stress_range_MPa": round(s_transition, 2),
        "selected_segment": segment,
        "standard": standard
    }
