import numpy as np
import os

def generate_series60_hull(
    loa: float,
    beam: float,
    draft: float,
    Cb: float,
    bow_type: str = "bulbous"
) -> str:
    """
    Generates a 3D parametric ship hull using an analytical waterline formula.
    Exports the shape as an ASCII STL mesh file.
    """
    # Create directory for output meshes
    mesh_dir = os.path.join(os.path.dirname(__file__), "meshes")
    os.makedirs(mesh_dir, exist_ok=True)
    mesh_path = os.path.join(mesh_dir, f"hull_loa{loa:.1f}_b{beam:.1f}_d{draft:.1f}_cb{Cb:.2f}_{bow_type}.stl")
    
    # Mesh discretization
    Nx = 40
    Nz = 15
    
    x_vals = np.linspace(-loa/2.0, loa/2.0, Nx)
    z_vals = np.linspace(-draft, 0.0, Nz)
    
    # Exponent for block coefficient control
    # Full block coefficient -> higher px (fuller hull amidships)
    px = max(1.1, Cb / (1.0 - Cb + 0.05))
    pz = 6.0 # flat bottom profile factor
    
    # Compute mesh vertices
    vertices = []
    # Grid of points
    grid_pts = np.zeros((Nx, Nz, 3))
    
    for i, x in enumerate(x_vals):
        # Normalize x coordinate to [-1, 1]
        x_norm = 2.0 * x / loa
        
        # Bulbous bow addition
        bulb_offset = 0.0
        if bow_type == "bulbous" and x_norm > 0.8:
            # Add a local swelling at the keel at the bow (x_norm close to 1, z close to keel -draft)
            # This is a beautiful physical feature!
            bulb_offset = 0.08 * beam * np.exp(-15.0 * (x_norm - 0.95)**2)
            
        for j, z in enumerate(z_vals):
            z_norm = z / draft # [-1, 0]
            
            # Parametric half-breadth
            y = (beam / 2.0) * (1.0 - np.abs(x_norm) ** px) * (1.0 - np.abs(z_norm) ** pz)
            
            # Apply bulbous bow thickness modification
            if bulb_offset > 0:
                # Bulb is largest at bottom-front
                y += bulb_offset * (1.0 - np.abs(z_norm + 0.7)**2)
                y = max(y, 0.005) # keep non-zero
                
            grid_pts[i, j] = [x, y, z]
            
    # Write STL file
    # We create triangles for port and starboard sides, bottom shell, and deck closing
    triangles = []
    
    def add_triangle(p1, p2, p3):
        # Compute normal
        v1 = p2 - p1
        v2 = p3 - p1
        n = np.cross(v1, v2)
        n_len = np.linalg.norm(n)
        if n_len > 1e-6:
            n = n / n_len
        else:
            n = np.array([0.0, 0.0, 0.0])
        triangles.append((n, p1, p2, p3))
        
    for i in range(Nx - 1):
        for j in range(Nz - 1):
            p00 = grid_pts[i, j]
            p10 = grid_pts[i+1, j]
            p01 = grid_pts[i, j+1]
            p11 = grid_pts[i+1, j+1]
            
            # Starboard side (y > 0)
            add_triangle(p00, p10, p11)
            add_triangle(p00, p11, p01)
            
            # Port side (y < 0) - mirror y
            p00_p = np.array([p00[0], -p00[1], p00[2]])
            p10_p = np.array([p10[0], -p10[1], p10[2]])
            p01_p = np.array([p01[0], -p01[1], p01[2]])
            p11_p = np.array([p11[0], -p11[1], p11[2]])
            
            add_triangle(p00_p, p11_p, p10_p)
            add_triangle(p00_p, p01_p, p11_p)
            
    # Close the transom stern (x = -loa/2) and bow stem (x = loa/2)
    # Bow stem (i = Nx-1) and transom stern (i = 0)
    for j in range(Nz - 1):
        p0_sb = grid_pts[0, j]
        p1_sb = grid_pts[0, j+1]
        p0_p = np.array([p0_sb[0], -p0_sb[1], p0_sb[2]])
        p1_p = np.array([p1_sb[0], -p1_sb[1], p1_sb[2]])
        
        # Transom closing
        add_triangle(p0_sb, p1_p, p0_p)
        add_triangle(p0_sb, p1_sb, p1_p)
        
    # Write to STL file
    with open(mesh_path, "w") as f:
        f.write(f"solid ship_hull\n")
        for n, p1, p2, p3 in triangles:
            f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n")
            f.write(f"    outer loop\n")
            f.write(f"      vertex {p1[0]:.6e} {p1[1]:.6e} {p1[2]:.6e}\n")
            f.write(f"      vertex {p2[0]:.6e} {p2[1]:.6e} {p2[2]:.6e}\n")
            f.write(f"      vertex {p3[0]:.6e} {p3[1]:.6e} {p3[2]:.6e}\n")
            f.write(f"    endloop\n")
            f.write(f"  endfacet\n")
        f.write("endsolid ship_hull\n")
        
    # Approximate hull surface area (sum of triangle areas)
    surface_area = 0.0
    for _, p1, p2, p3 in triangles:
        # standard triangle area formula
        a = np.linalg.norm(np.cross(p2 - p1, p3 - p1)) * 0.5
        surface_area += a
        
    return mesh_path, round(surface_area, 2)
