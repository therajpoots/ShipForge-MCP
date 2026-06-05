import numpy as np

def generate_lhs_samples(n_samples: int = 20) -> list:
    """
    Generates initial ship design parameter configurations using Latin Hypercube Sampling.
    Parameters to sample:
    - LOA: 100m to 200m
    - Beam: 15m to 30m
    - Draft: 5m to 12m
    - Cb: 0.60 to 0.82
    - Bow Type: 'bulbous' or 'conventional'
    """
    # Sample 4 continuous variables in normalized LHS intervals [0, 1]
    np.random.seed(42) # reproducible initial design seed
    
    # LHS grid
    grid = np.zeros((n_samples, 4))
    for i in range(4):
        # Create bins
        bins = np.linspace(0.0, 1.0, n_samples + 1)
        # Random point inside each bin
        bin_pts = bins[:-1] + np.random.rand(n_samples) * (bins[1:] - bins[:-1])
        # Shuffle bin allocations
        np.random.shuffle(bin_pts)
        grid[:, i] = bin_pts
        
    population = []
    for i in range(n_samples):
        # Scale to physical design ranges
        loa = 100.0 + grid[i, 0] * 100.0 # 100 to 200
        # Restrict Beam relative to LOA (L/B typically 5.5 to 8.0)
        lb_ratio = 5.5 + grid[i, 1] * 2.5
        beam = loa / lb_ratio
        
        # Restrict Draft relative to Beam (B/T typically 2.2 to 3.5)
        bt_ratio = 2.2 + grid[i, 2] * 1.3
        draft = beam / bt_ratio
        
        # Block coefficient
        Cb = 0.60 + grid[i, 3] * 0.22 # 0.60 to 0.82
        
        # Bow Type
        bow = "bulbous" if i % 2 == 0 else "conventional"
        
        population.append({
            "design_id": f"SF-LHS-{i+1:02d}",
            "hull": {
                "loa": round(float(loa), 1),
                "beam": round(float(beam), 1),
                "draft": round(float(draft), 1),
                "Cb": round(float(Cb), 2),
                "bow_type": bow
            }
        })
        
    return population

def compute_pareto_front(designs: list) -> list:
    """
    Performs non-dominated sorting on the design population.
    Objectives (to minimize):
    1. Drag: total_resistance_kN
    2. Weight: section_weight_index (kg/m^2)
    3. Fatigue Damage: cumulative_fatigue_damage
    
    A design A dominates B if it is better or equal in all objectives,
    and strictly better in at least one objective.
    """
    pareto_set = []
    
    # Extract objective vectors
    objectives = []
    valid_designs = []
    
    for d in designs:
        cfd = d.get("cfd", {})
        scantlings = d.get("scantlings", {})
        fatigue = d.get("fatigue", {})
        
        # Ensure the design has successful outputs
        if not cfd or not scantlings or not fatigue:
            continue
            
        drag = cfd.get("total_resistance_kN", 999.0)
        weight = scantlings.get("required_thickness_mm", 15.0) * 7.85 # proportional to thickness
        damage = fatigue.get("cumulative_fatigue_damage", 9.9)
        
        objectives.append([drag, weight, damage])
        valid_designs.append(d)
        
    n = len(valid_designs)
    if n == 0:
        return []
        
    objs = np.array(objectives)
    dominated = np.zeros(n, dtype=bool)
    
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # Check if design j dominates design i
            # j dominates i if all elements in objs[j] <= objs[i] and at least one element is strictly smaller
            if np.all(objs[j] <= objs[i]) and np.any(objs[j] < objs[i]):
                dominated[i] = True
                break
                
    # Non-dominated designs belong to the Pareto front
    for i in range(n):
        if not dominated[i]:
            valid_designs[i]["pareto_optimal"] = True
            pareto_set.append(valid_designs[i])
        else:
            valid_designs[i]["pareto_optimal"] = False
            
    return pareto_set
