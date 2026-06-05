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

if __name__ == "__main__":
    create_architecture_diagram()
