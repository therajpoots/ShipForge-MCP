import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "materials.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create materials table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS materials (
        material_id TEXT PRIMARY KEY,
        name TEXT,
        class TEXT,
        grade TEXT,
        yield_strength_MPa REAL,
        uts_MPa REAL,
        elongation_pct REAL,
        density_kg_m3 REAL,
        youngs_modulus_GPa REAL,
        source TEXT
    )
    """)

    # Create sn_curves table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sn_curves (
        curve_id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id TEXT,
        environment TEXT,
        weld_class TEXT,
        log_k1 REAL,
        m1 REAL,
        log_k2 REAL,
        m2 REAL,
        transition_n REAL,
        standard TEXT,
        FOREIGN KEY (material_id) REFERENCES materials(material_id)
    )
    """)

    # Populate materials
    materials_data = [
        ("NV-A", "Mild steel NV-A", "steel", "NV-A", 235.0, 400.0, 22.0, 7850.0, 206.0, "DNV-GL Rules Part 3 Ch 1"),
        ("NV-AH32", "High-strength steel NV-AH32", "steel", "NV-AH32", 315.0, 440.0, 20.0, 7850.0, 206.0, "DNV-GL Rules Part 3 Ch 1"),
        ("NV-AH36", "High-strength steel NV-AH36", "steel", "NV-AH36", 355.0, 490.0, 19.0, 7850.0, 206.0, "DNV-GL Rules Part 3 Ch 1"),
        ("NV-AH40", "High-strength steel NV-AH40", "steel", "NV-AH40", 390.0, 510.0, 19.0, 7850.0, 206.0, "DNV-GL Rules Part 3 Ch 1"),
        ("AL-5083", "Marine-grade Aluminium 5083-H321", "aluminium", "5083-H321", 228.0, 317.0, 12.0, 2660.0, 70.0, "ASTM B209"),
        ("AL-6061", "Structural Aluminium 6061-T6", "aluminium", "6061-T6", 276.0, 310.0, 12.0, 2700.0, 68.9, "ASTM B209"),
        ("FRP-POLY", "Glass Fiber Reinforced Polyester", "frp", "FRP-Polyester", 150.0, 250.0, 2.0, 1800.0, 20.0, "Composite Materials Handbooks"),
        ("CFRP-EPOXY", "Carbon Fiber Reinforced Epoxy", "cfrp", "CFRP-Epoxy", 800.0, 1200.0, 1.5, 1600.0, 135.0, "Composite Materials Handbooks")
    ]

    cursor.executemany("""
    INSERT OR REPLACE INTO materials 
    (material_id, name, class, grade, yield_strength_MPa, uts_MPa, elongation_pct, density_kg_m3, youngs_modulus_GPa, source)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, materials_data)

    # Populate S-N curves (DNV-RP-C203 / DNV-GL-SE-0567 values for welded joints in steel)
    # Weld class D, E, F, F2, G, W, B, C
    # In air, seawater with cathodic protection (CP), seawater free corrosion (FC)
    sn_data = [
        # Material NV-A (and other steels - we link curves by material ID, but they share rules)
        # Steel DNV S-N curves (DNV-RP-C203)
        # Weld Class D (Base material with attachment / weld detail)
        (None, "NV-A", "air", "D", 12.187, 3.0, 15.645, 5.0, 1e7, "DNV-RP-C203"),
        (None, "NV-A", "seawater_cp", "D", 12.187, 3.0, 15.645, 5.0, 1e6, "DNV-RP-C203"),
        (None, "NV-A", "seawater", "D", 11.687, 3.0, 11.687, 3.0, 1e20, "DNV-RP-C203 (FC)"), # single slope

        # Weld Class F (Transverse butt weld)
        (None, "NV-A", "air", "F", 11.855, 3.0, 15.092, 5.0, 1e7, "DNV-RP-C203"),
        (None, "NV-A", "seawater_cp", "F", 11.855, 3.0, 15.092, 5.0, 1e6, "DNV-RP-C203"),
        (None, "NV-A", "seawater", "F", 11.355, 3.0, 11.355, 3.0, 1e20, "DNV-RP-C203 (FC)"),

        # High-strength steels share the same curves as they are based on structural weld details (geometry governs fatigue)
        (None, "NV-AH32", "air", "D", 12.187, 3.0, 15.645, 5.0, 1e7, "DNV-RP-C203"),
        (None, "NV-AH32", "seawater_cp", "D", 12.187, 3.0, 15.645, 5.0, 1e6, "DNV-RP-C203"),
        (None, "NV-AH32", "seawater", "D", 11.687, 3.0, 11.687, 3.0, 1e20, "DNV-RP-C203 (FC)"),
        (None, "NV-AH32", "air", "F", 11.855, 3.0, 15.092, 5.0, 1e7, "DNV-RP-C203"),
        
        (None, "NV-AH36", "air", "D", 12.187, 3.0, 15.645, 5.0, 1e7, "DNV-RP-C203"),
        (None, "NV-AH36", "seawater_cp", "D", 12.187, 3.0, 15.645, 5.0, 1e6, "DNV-RP-C203"),
        (None, "NV-AH36", "seawater", "D", 11.687, 3.0, 11.687, 3.0, 1e20, "DNV-RP-C203 (FC)"),
        (None, "NV-AH36", "air", "F", 11.855, 3.0, 15.092, 5.0, 1e7, "DNV-RP-C203"),
        (None, "NV-AH36", "seawater_cp", "F", 11.855, 3.0, 15.092, 5.0, 1e6, "DNV-RP-C203"),

        (None, "NV-AH40", "air", "D", 12.187, 3.0, 15.645, 5.0, 1e7, "DNV-RP-C203"),
        (None, "NV-AH40", "seawater_cp", "D", 12.187, 3.0, 15.645, 5.0, 1e6, "DNV-RP-C203"),
        
        # Aluminium S-N Curves (typically single-slope or slightly different coefficients, e.g. BS 8118 / DNV-RP-C203 for Al)
        # We model them using log_k1, m1, etc.
        (None, "AL-5083", "air", "D", 11.8, 3.5, 11.8, 3.5, 1e20, "DNV-Aluminium-Design"),
        (None, "AL-5083", "seawater", "D", 11.2, 3.5, 11.2, 3.5, 1e20, "DNV-Aluminium-Design (FC)"),
        (None, "AL-6061", "air", "D", 11.9, 3.4, 11.9, 3.4, 1e20, "ASTM-Al-Fatigue")
    ]

    cursor.executemany("""
    INSERT OR REPLACE INTO sn_curves 
    (curve_id, material_id, environment, weld_class, log_k1, m1, log_k2, m2, transition_n, standard)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sn_data)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
