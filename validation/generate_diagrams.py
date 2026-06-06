import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def create_architecture_diagram():
    # Set high-resolution canvas (1600 x 1200)
    width, height = 1600, 1200
    # Create background with soft gradient
    image = Image.new("RGBA", (width, height), (15, 23, 42, 255)) # Dark navy (#0F172A)
    draw = ImageDraw.Draw(image)
    
    # Try to load fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 40)
        font_subtitle = ImageFont.truetype("arial.ttf", 20)
        font_bold = ImageFont.truetype("arialbd.ttf", 22)
        font_regular = ImageFont.truetype("arial.ttf", 16)
        font_arrow = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        # Fallback to default if Arial is not found (unlikely on Windows)
        font_title = ImageFont.load_default()
        font_subtitle = font_title
        font_bold = font_title
        font_regular = font_title
        font_arrow = font_title

    # Draw a soft radial gradient highlight in the center
    for r in range(600, 0, -10):
        alpha = int(45 * (1 - r / 600.0))
        draw.ellipse([width//2 - r, height//2 - r, width//2 + r, height//2 + r], fill=(59, 130, 246, alpha))

    # Define layout coordinates for components
    # Center: Orchestrator
    orch_box = [width//2 - 180, height//2 - 90, width//2 + 180, height//2 + 90]
    
    # Orbiting MCP Servers (6 servers arranged in a circle)
    # Radii of orbit
    rx, ry = 500, 350
    center_x, center_y = width//2, height//2
    
    servers_info = [
        {
            "name": "Hull CFD Server",
            "role": "Hydrodynamic Evaluation",
            "color": (16, 185, 129), # Emerald green (#10B981)
            "angle": 0, # Right
            "details": ["• Holtrop-Mennen Fallback", "• Series 60 STL Gen", "• Wake Fraction Reg.", "• Seakeeping (RAO/MSI)"]
        },
        {
            "name": "Rule Engine Server",
            "role": "Classification Compliance",
            "color": (245, 158, 11), # Amber orange (#F59E0B)
            "angle": 60, # Bottom Right
            "details": ["• DNV Pt 3 Ch 1 Scantling", "• Intact Stability GM/L", "• Section Modulus Check", "• Buckling Pan Utilization"]
        },
        {
            "name": "Structural FEA Server",
            "role": "Global Loading & Stress",
            "color": (239, 68, 68), # Red (#EF4444)
            "angle": 120, # Bottom Left
            "details": ["• Girder Bending Moment", "• Local Stress Solver", "• Miner's Load Spectrum", "• Cumulative Damage (0.15x)"]
        },
        {
            "name": "Fatigue ML Server",
            "role": "Surrogate Fatigue Inference",
            "color": (139, 92, 246), # Purple (#8B5CF6)
            "angle": 180, # Left
            "details": ["• GBR Fatigue Surrogate", "• Physics-Informed (15k)", "• Weld Detail Classifier", "• log10(Cycles) Predictor"]
        },
        {
            "name": "Material DB Server",
            "role": "Materials & S-N Curves",
            "color": (59, 130, 246), # Blue (#3B82F6)
            "angle": 240, # Top Left
            "details": ["• SQLite Material Schema", "• DNV-RP-C203 Coefficients", "• Corrosion Degradation", "• Temperature Viscosity"]
        },
        {
            "name": "Report & CAD Server",
            "role": "Documentation & Exports",
            "color": (6, 182, 212), # Cyan (#06B6D4)
            "angle": 300, # Top Right
            "details": ["• IGES NURBS CAD Exporter", "• ReportLab PDF Gen", "• Co-Opt Audit Log JSON", "• Structural Plot Embeds"]
        }
    ]

    # Draw Title
    draw.text((width//2, 60), "MCP-ShipForge: Multi-Agent Co-Optimization Architecture", fill=(255, 255, 255, 255), font=font_title, anchor="ms")
    draw.text((width//2, 100), "Agentic Model Context Protocol (MCP) Framework for Intelligent Shipbuilding Design", fill=(148, 163, 184, 255), font=font_subtitle, anchor="ms")

    # Draw Orchestrator Box (Glassmorphic look)
    # Background shadow/glow
    draw.rounded_rectangle([orch_box[0]-4, orch_box[1]-4, orch_box[2]+4, orch_box[3]+4], radius=15, fill=(30, 41, 59, 100), outline=(59, 130, 246, 200), width=2)
    draw.rounded_rectangle(orch_box, radius=12, fill=(15, 23, 42, 230), outline=(96, 165, 250, 255), width=2)
    
    # Orchestrator Text
    draw.text((center_x, center_y - 40), "AGENTIC ORCHESTRATOR", fill=(96, 165, 250, 255), font=font_bold, anchor="mm")
    draw.text((center_x, center_y - 10), "(DeepSeek LLM Backbone)", fill=(255, 255, 255, 255), font=font_bold, anchor="mm")
    draw.text((center_x, center_y + 20), "• Coordinates Co-Optimization", fill=(226, 232, 240, 255), font=font_regular, anchor="mm")
    draw.text((center_x, center_y + 40), "• Runs Multi-Server JSON-RPC Loop", fill=(226, 232, 240, 255), font=font_regular, anchor="mm")
    draw.text((center_x, center_y + 60), "• Computes Pareto Multi-Objective Front", fill=(226, 232, 240, 255), font=font_regular, anchor="mm")

    # Draw Servers and Arrows
    for idx, s in enumerate(servers_info):
        # Calculate server center position in ellipse orbit
        rad = np.radians(s["angle"])
        s_cx = int(center_x + rx * np.cos(rad))
        s_cy = int(center_y + ry * np.sin(rad))
        
        # Server box dimensions
        w_box, h_box = 300, 160
        box = [s_cx - w_box//2, s_cy - h_box//2, s_cx + w_box//2, s_cy + h_box//2]
        
        # Color definitions
        r_c, g_c, b_c = s["color"]
        
        # Draw Server Box
        draw.rounded_rectangle([box[0]-2, box[1]-2, box[2]+2, box[3]+2], radius=10, fill=(30, 41, 59, 80), outline=(r_c, g_c, b_c, 100), width=1)
        draw.rounded_rectangle(box, radius=8, fill=(15, 23, 42, 240), outline=(r_c, g_c, b_c, 255), width=2)
        
        # Server Text
        draw.text((s_cx, s_cy - h_box//2 + 25), s["name"].upper(), fill=(r_c, g_c, b_c, 255), font=font_bold, anchor="mm")
        draw.text((s_cx, s_cy - h_box//2 + 48), f"Role: {s['role']}", fill=(148, 163, 184, 255), font=font_subtitle, anchor="mm")
        
        # Details text
        for line_idx, detail in enumerate(s["details"]):
            draw.text((s_cx - w_box//2 + 20, s_cy - h_box//2 + 75 + line_idx * 20), detail, fill=(226, 232, 240, 255), font=font_regular)

        # Draw Communication Line (Double-sided arrows) between Orchestrator and Server
        # Boundary intersection points
        # Orchestrator boundary point
        dir_x = s_cx - center_x
        dir_y = s_cy - center_y
        dist = np.sqrt(dir_x**2 + dir_y**2)
        ux, uy = dir_x / dist, dir_y / dist
        
        # Start line from Orchestrator boundary
        # For simplicity, approximate border intersection
        start_x = int(center_x + 180 * np.sign(ux) if abs(ux) > 0.8 else center_x + ux * 180)
        start_y = int(center_y + 90 * np.sign(uy) if abs(uy) > 0.8 else center_y + uy * 90)
        
        # Adjust start points based on quadrant
        if abs(ux) > abs(uy):
            start_x = int(center_x + np.sign(ux) * 180)
            start_y = int(center_y + (uy/abs(ux)) * 90)
        else:
            start_x = int(center_x + (ux/abs(uy)) * 180)
            start_y = int(center_y + np.sign(uy) * 90)
            
        # End line at Server boundary
        if abs(ux) > abs(uy):
            end_x = int(s_cx - np.sign(ux) * w_box//2)
            end_y = int(s_cy - (uy/abs(ux)) * h_box//2)
        else:
            end_x = int(s_cx - (ux/abs(uy)) * w_box//2)
            end_y = int(s_cy - np.sign(uy) * h_box//2)
            
        # Draw the connection line (JSON-RPC pipe)
        draw.line([start_x, start_y, end_x, end_y], fill=(96, 165, 250, 120), width=3)
        
        # Draw arrowheads
        # From Orchestrator to Server arrowhead
        ax1 = end_x - int(15 * ux)
        ay1 = end_y - int(15 * uy)
        # perpendicular vector
        px, py = -uy, ux
        draw.polygon([end_x, end_y, ax1 + int(6 * px), ay1 + int(6 * py), ax1 - int(6 * px), ay1 - int(6 * py)], fill=(96, 165, 250, 255))
        
        # From Server to Orchestrator arrowhead
        ax2 = start_x + int(15 * ux)
        ay2 = start_y + int(15 * uy)
        draw.polygon([start_x, start_y, ax2 + int(6 * px), ay2 + int(6 * py), ax2 - int(6 * px), ay2 - int(6 * py)], fill=(96, 165, 250, 255))
        
        # Add "JSON-RPC" protocol label on arrows
        label_x = int(start_x + 0.45 * (end_x - start_x))
        label_y = int(start_y + 0.45 * (end_y - start_y)) - 10
        draw.text((label_x, label_y), "JSON-RPC", fill=(96, 165, 250, 180), font=font_arrow, anchor="mm")

    # Draw Legend or Footer
    draw.rounded_rectangle([40, height - 100, width - 40, height - 40], radius=8, fill=(15, 23, 42, 200), outline=(71, 85, 105, 100), width=1)
    draw.text((width//2, height - 70), "Co-optimization loop: 1. Generate LHS hulls -> 2. CFD Resistance -> 3. Rule Scantlings -> 4. FEA Girders & Stresses -> 5. ML Fatigue -> 6. Intact Stability GM/L -> 7. PDF CAD Report", fill=(148, 163, 184, 255), font=font_subtitle, anchor="mm")

    # Save to disk
    plots_dir = "validation/plots"
    os.makedirs(plots_dir, exist_ok=True)
    out_path = os.path.join(plots_dir, "architecture_flowchart.png")
    image.save(out_path)
    print(f"Flowchart successfully generated and saved to {out_path}")

def create_midship_diagram():
    # Set high-resolution canvas (1200 x 800)
    width, height = 1200, 800
    # Create background with soft gradient
    image = Image.new("RGBA", (width, height), (15, 23, 42, 255)) # Dark navy (#0F172A)
    draw = ImageDraw.Draw(image)
    
    # Try to load fonts
    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_subtitle = ImageFont.truetype("arial.ttf", 18)
        font_bold = ImageFont.truetype("arialbd.ttf", 20)
        font_regular = ImageFont.truetype("arial.ttf", 16)
        font_dim = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font_title = ImageFont.load_default()
        font_subtitle = font_title
        font_bold = font_title
        font_regular = font_title
        font_dim = font_title

    # Draw Title
    draw.text((width//2, 50), "Stiffened Box Girder Midship Section Model", fill=(255, 255, 255, 255), font=font_title, anchor="ms")
    draw.text((width//2, 85), "Idealized structural cross-section for section modulus & FEA stress analysis", fill=(148, 163, 184, 255), font=font_subtitle, anchor="ms")

    # Center coordinates of the cross-section box
    cx, cy = 600, 430
    box_w, box_h = 500, 320  # Breadth B = 500, Depth D = 320
    
    # Coordinates of box corners
    left = cx - box_w//2   # 350
    right = cx + box_w//2  # 850
    top = cy - box_h//2    # 270
    bottom = cy + box_h//2 # 590
    
    # Draw radial glow under the box girder
    for r in range(400, 0, -10):
        alpha = int(30 * (1 - r / 400.0))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(59, 130, 246, alpha))

    # Colors
    color_plate = (148, 163, 184, 255)       # Slate blue/grey for plates
    color_stiffener = (56, 189, 248, 255)     # Sky blue for stiffeners
    color_dim = (245, 158, 11, 255)           # Amber for dimension lines
    color_label = (226, 232, 240, 255)         # Off-white for general text
    
    # 1. Draw Plate Panels (Thick rectangles)
    # Deck Plating (Top)
    draw.rectangle([left - 5, top - 6, right + 5, top + 4], fill=color_plate)
    # Bottom Plating (Bottom)
    draw.rectangle([left - 5, bottom - 4, right + 5, bottom + 6], fill=color_plate)
    # Side Shell Plating (Left & Right)
    draw.rectangle([left - 10, top + 4, left, bottom - 4], fill=color_plate)
    draw.rectangle([right, top + 4, right + 10, bottom - 4], fill=color_plate)
    
    # 2. Draw Longitudinal Stiffeners (Spacing s)
    # Draw T-stiffeners on deck and bottom
    num_stiffeners = 9
    stiff_xs = np.linspace(left + 50, right - 50, num_stiffeners)
    stiff_h = 24  # height of stiffener web
    flange_w = 14 # width of flange
    
    for x in stiff_xs:
        x_int = int(x)
        # Top deck stiffeners (pointing downwards)
        # Web
        draw.rectangle([x_int - 2, top + 4, x_int + 2, top + 4 + stiff_h], fill=color_stiffener)
        # Flange
        draw.rectangle([x_int - flange_w//2, top + 4 + stiff_h, x_int + flange_w//2, top + 4 + stiff_h + 4], fill=color_stiffener)
        
        # Bottom deck stiffeners (pointing upwards)
        # Web
        draw.rectangle([x_int - 2, bottom - 4 - stiff_h, x_int + 2, bottom - 4], fill=color_stiffener)
        # Flange
        draw.rectangle([x_int - flange_w//2, bottom - 4 - stiff_h - 4, x_int + flange_w//2, bottom - 4 - stiff_h], fill=color_stiffener)

    # 3. Dimension line for Beam (B) - above top deck
    dim_y = top - 70
    draw.line([left, dim_y, right, dim_y], fill=color_dim, width=2)
    # Dashed/dotted extension lines
    for dy in range(dim_y - 10, top - 5, 4):
        draw.line([left, dy, left, dy+2], fill=(100, 116, 139, 255), width=1)
        draw.line([right, dy, right, dy+2], fill=(100, 116, 139, 255), width=1)
    # Arrow heads for Beam B
    draw.polygon([left, dim_y, left + 12, dim_y - 5, left + 12, dim_y + 5], fill=color_dim)
    draw.polygon([right, dim_y, right - 12, dim_y - 5, right - 12, dim_y + 5], fill=color_dim)
    # Label for Beam B
    draw.text((cx, dim_y - 20), "Beam (B)", fill=color_dim, font=font_bold, anchor="mm")
    
    # 4. Dimension line for Depth (D) - to the left of the shell
    dim_x = left - 120
    draw.line([dim_x, top, dim_x, bottom], fill=color_dim, width=2)
    # Extension lines
    for dx in range(dim_x - 10, left - 10, 4):
        draw.line([dx, top, dx+2, top], fill=(100, 116, 139, 255), width=1)
        draw.line([dx, bottom, dx+2, bottom], fill=(100, 116, 139, 255), width=1)
    # Arrow heads for Depth D
    draw.polygon([dim_x, top, dim_x - 5, top + 12, dim_x + 5, top + 12], fill=color_dim)
    draw.polygon([dim_x, bottom, dim_x - 5, bottom - 12, dim_x + 5, bottom - 12], fill=color_dim)
    # Label for Depth D
    draw.text((dim_x - 25, cy), "Depth (D)", fill=color_dim, font=font_bold, anchor="rm")

    # 5. Dimension line for Stiffener Spacing (s)
    s_x1 = int(stiff_xs[3])
    s_x2 = int(stiff_xs[4])
    s_cy = bottom - 50
    draw.line([s_x1, s_cy, s_x2, s_cy], fill=color_dim, width=2)
    # Arrow heads for spacing s
    draw.polygon([s_x1, s_cy, s_x1 + 6, s_cy - 3, s_x1 + 6, s_cy + 3], fill=color_dim)
    draw.polygon([s_x2, s_cy, s_x2 - 6, s_cy - 3, s_x2 - 6, s_cy + 3], fill=color_dim)
    # Label for spacing s
    draw.text(((s_x1 + s_x2)//2, s_cy - 15), "Spacing (s)", fill=color_dim, font=font_dim, anchor="mm")

    # 6. Labels and Arrow Callouts
    # Label: Deck Plating
    draw.text((right + 120, top - 30), "Deck Plating", fill=color_label, font=font_bold, anchor="lm")
    # Draw arrow from label to deck plating
    draw.line([right + 110, top - 30, right + 10, top - 15, cx + 100, top], fill=(148, 163, 184, 180), width=2)
    draw.polygon([cx + 100, top, cx + 110, top - 6, cx + 108, top + 6], fill=(148, 163, 184, 255))
    
    # Label: Side Shell Plating
    draw.text((right + 120, cy), "Side Shell Plating", fill=color_label, font=font_bold, anchor="lm")
    # Draw arrow to side shell plating
    draw.line([right + 110, cy, right + 5, cy], fill=(148, 163, 184, 180), width=2)
    draw.polygon([right + 5, cy, right + 15, cy - 5, right + 15, cy + 5], fill=(148, 163, 184, 255))
    
    # Label: Bottom Plating
    draw.text((right + 120, bottom + 30), "Bottom Plating", fill=color_label, font=font_bold, anchor="lm")
    # Draw arrow to bottom plating
    draw.line([right + 110, bottom + 30, right + 10, bottom + 15, cx + 100, bottom], fill=(148, 163, 184, 180), width=2)
    draw.polygon([cx + 100, bottom, cx + 108, bottom - 6, cx + 110, bottom + 6], fill=(148, 163, 184, 255))
    
    # Label: Longitudinal Stiffeners
    draw.text((cx - 100, bottom + 110), "Longitudinal Stiffeners", fill=color_stiffener, font=font_bold, anchor="mm")
    # Draw arrow to one of bottom stiffeners
    stiff_target_x = int(stiff_xs[2])
    draw.line([cx - 100, bottom + 95, cx - 120, bottom + 60, stiff_target_x, bottom - 15], fill=(56, 189, 248, 180), width=2)
    draw.polygon([stiff_target_x, bottom - 15, stiff_target_x - 6, bottom - 25, stiff_target_x + 6, bottom - 25], fill=color_stiffener)

    # Save to disk
    plots_dir = "validation/plots"
    os.makedirs(plots_dir, exist_ok=True)
    out_path = os.path.join(plots_dir, "midship_section.png")
    image.save(out_path)
    print(f"Midship section diagram successfully generated and saved to {out_path}")

if __name__ == "__main__":
    create_architecture_diagram()
    create_midship_diagram()
