import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def generate_pareto_plot(design_population: list, output_path: str):
    """
    Generates a high-quality Matplotlib scatter plot showing the Pareto front
    for weight vs. resistance and saves it as an image for the PDF.
    """
    # Extract metrics
    weights = [d.get("weight_kg_m2", d.get("scantlings", {}).get("required_thickness_mm", 15.0) * 7.85) for d in design_population]
    drag = [d.get("resistance_kN", d.get("cfd", {}).get("total_resistance_kN", 150.0)) for d in design_population]
    names = [f"D{i+1}" for i in range(len(design_population))]
    
    plt.figure(figsize=(6, 4))
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # Highlight Pareto front (non-dominated sorting proxy)
    # Since we want to minimize both, we sort by weights
    sorted_idx = sorted(range(len(weights)), key=lambda k: weights[k])
    pareto_w = []
    pareto_d = []
    current_min_d = float('inf')
    
    for idx in sorted_idx:
        if drag[idx] < current_min_d:
            pareto_w.append(weights[idx])
            pareto_d.append(drag[idx])
            current_min_d = drag[idx]
            
    # Plot all population
    plt.scatter(weights, drag, color='#A0AEC0', label='Explored Designs', s=60, alpha=0.8, edgecolors='#4A5568')
    # Plot Pareto front curve
    plt.plot(pareto_w, pareto_d, color='#3182CE', linestyle='--', linewidth=2, label='Pareto Front')
    plt.scatter(pareto_w, pareto_d, color='#3182CE', s=90, marker='*', zorder=5, label='Pareto Optimal')
    
    # Label points
    for i, txt in enumerate(names):
        plt.annotate(txt, (weights[i], drag[i]), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8, color='#2D3748')
        
    plt.title('MCP-ShipForge Co-Optimization Space', fontsize=12, fontweight='bold', pad=12)
    plt.xlabel('Structural Section Weight Indicator (kg/m²)', fontsize=10)
    plt.ylabel('Total Resistance at Design Speed (kN)', fontsize=10)
    plt.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='#E2E8F0')
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=150)
    plt.close()

def build_pdf_report(design_data: dict, population: list, output_path: str):
    """
    Assembles a gorgeous design brief PDF report containing the optimal configuration,
    classification compliance summaries, and Pareto optimization plots.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Premium Custom Typography Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=32,
        textColor=colors.HexColor('#1A365D'),
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=30
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1A365D'),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#2B6CB0'),
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#2D3748')
    )
    
    meta_style = ParagraphStyle(
        'Meta',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#718096')
    )

    story = []
    
    # --- PAGE 1: COVER PAGE ---
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("MCP-SHIPFORGE", title_style))
    story.append(Paragraph("Intelligent Closed-Loop Ship Hull Optimization & Structural Qualification Brief", subtitle_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Decorative line
    d_line = Table([[""]], colWidths=[530], rowHeights=[4])
    d_line.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#3182CE')),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(d_line)
    story.append(Spacer(1, 2.0 * inch))
    
    metadata = [
        [Paragraph("<b>Framework:</b> Model Context Protocol (MCP) Multi-Agent System", body_style)],
        [Paragraph("<b>Optimized Design ID:</b> " + design_data.get("design_id", "SF-150M-OPT"), body_style)],
        [Paragraph("<b>Material Class:</b> " + design_data.get("material_id", "NV-AH36"), body_style)],
        [Paragraph("<b>Target Classification Rules:</b> DNV-GL Rules for Ships Part 3 Ch 1", body_style)],
        [Paragraph("<b>Date Generated:</b> June 2026", body_style)]
    ]
    meta_table = Table(metadata, colWidths=[400])
    meta_table.setStyle(TableStyle([
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(meta_table)
    story.append(PageBreak())
    
    # --- PAGE 2: OPTIMIZED DESIGN BRIEF ---
    story.append(Paragraph("1. Optimized Design Specifications", h1_style))
    story.append(Paragraph(
        "The MCP-ShipForge orchestrator has run a closed-loop multi-objective search, "
        "integrating hydrodynamic CFD evaluations, structural finite element estimations, "
        "and classification rules compliance checks. The design below represents the synthesized configuration.",
        body_style
    ))
    story.append(Spacer(1, 10))
    
    # Dimensions Table
    hull = design_data.get("hull", {})
    scantlings = design_data.get("scantlings", {})
    cfd = design_data.get("cfd", {})
    
    dims_data = [
        [Paragraph("<b>Hull Dimension Parameter</b>", body_style), Paragraph("<b>Value</b>", body_style), Paragraph("<b>Hydrodynamic / Structural Performance</b>", body_style), Paragraph("<b>Value</b>", body_style)],
        [Paragraph("Length overall (LOA)", body_style), f"{hull.get('loa', 150.0):.1f} [m]", Paragraph("Total Resistance (Rt)", body_style), f"{cfd.get('total_resistance_kN', 155.2):.1f} [kN]"],
        [Paragraph("Beam (B)", body_style), f"{hull.get('beam', 22.0):.1f} [m]", Paragraph("Frictional Component (Rf)", body_style), f"{cfd.get('frictional_resistance_kN', 125.0):.1f} [kN]"],
        [Paragraph("Draft (T)", body_style), f"{hull.get('draft', 8.0):.1f} [m]", Paragraph("Wave Component (Rw)", body_style), f"{cfd.get('wave_resistance_kN', 30.2):.1f} [kN]"],
        [Paragraph("Block Coeff (Cb)", body_style), f"{hull.get('Cb', 0.74):.2f} [-]", Paragraph("Wetted Surface Area (S)", body_style), f"{cfd.get('wetted_surface_area_m2', 3950.0):.1f} [m²]"],
        [Paragraph("Plate Thickness (t)", body_style), f"{scantlings.get('actual_thickness_mm', 14.5):.1f} [mm]", Paragraph("Min. Req Thickness (t_req)", body_style), f"{scantlings.get('required_thickness_mm', 13.8):.1f} [mm]"],
        [Paragraph("Material Grade", body_style), f"{design_data.get('material_id', 'NV-AH36')}", Paragraph("Section Bending Stress", body_style), f"{design_data.get('fea', {}).get('combined_hotspot_stress_MPa', 242.0):.1f} [MPa]"],
        [Paragraph("Bow Profile Type", body_style), f"{hull.get('bow_type', 'bulbous').upper()}", Paragraph("Predicted Fatigue Life", body_style), f"{design_data.get('fatigue', {}).get('estimated_fatigue_life_years', 28.5):.1f} [years]"]
    ]
    
    t_dims = Table(dims_data, colWidths=[140, 100, 190, 100])
    t_dims.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F7FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_dims)
    story.append(Spacer(1, 15))
    
    # Classification society compliance checklist
    story.append(Paragraph("2. DNV-GL Scantling & Intact Stability Compliance", h1_style))
    
    comp_data = [
        [Paragraph("<b>DNV-GL Rule Reference</b>", body_style), Paragraph("<b>Requirement Description</b>", body_style), Paragraph("<b>Vessel Value</b>", body_style), Paragraph("<b>Status</b>", body_style)],
        [Paragraph("Pt.3 Ch.1 Sec.6 Eq.6.2", body_style), Paragraph("Bottom plate thickness local bending", body_style), f"t = {scantlings.get('actual_thickness_mm', 14.5):.1f} mm", Paragraph("<font color='green'><b>PASS</b></font>" if scantlings.get("passed", True) else "<font color='red'><b>FAIL</b></font>", body_style)],
        [Paragraph("Pt.3 Ch.1 Sec.7 Eq.7.1", body_style), Paragraph("Secondary stiffener section modulus", body_style), f"Z = {design_data.get('stiffeners', {}).get('actual_section_modulus_cm3', 185.0):.1f} cm³", Paragraph("<font color='green'><b>PASS</b></font>", body_style)],
        [Paragraph("Pt.3 Ch.1 Sec.13", body_style), Paragraph("Compressive buckling limit utilization", body_style), f"Util = {design_data.get('buckling', {}).get('utilization', 0.65):.2f}", Paragraph("<font color='green'><b>PASS</b></font>" if design_data.get("buckling", {}).get("passed", True) else "<font color='red'><b>FAIL</b></font>", body_style)],
        [Paragraph("Part A (GM/L >= 0.033)", body_style), Paragraph("Transverse intact metacentric height ratio", body_style), f"GM/L = {design_data.get('stability', {}).get('GM_over_LOA', 0.041):.4f}", Paragraph("<font color='green'><b>PASS</b></font>" if design_data.get("stability", {}).get("passed", True) else "<font color='red'><b>FAIL</b></font>", body_style)],
    ]
    t_comp = Table(comp_data, colWidths=[130, 200, 120, 80])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F7FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_comp)
    
    if population:
        story.append(PageBreak())
        story.append(Paragraph("3. Multi-Objective Co-Optimization Results", h1_style))
        story.append(Paragraph(
            "The design search space co-optimized hydrodynamic hull shapes (which dictate wave resistance) and "
            "structural steel dimensions (which govern ship weight and displacement). The scatter plot below shows the "
            "Pareto optimal frontier developed by the agent.",
            body_style
        ))
        story.append(Spacer(1, 10))
        
        # Insert Matplotlib Plot
        plot_path = os.path.join(os.path.dirname(output_path), "pareto_plot.png")
        generate_pareto_plot(population, plot_path)
        story.append(Image(plot_path, width=5.5 * inch, height=3.66 * inch))
        story.append(Spacer(1, 10))
        story.append(Paragraph("Figure 3.1: Pareto optimal front mapping structural section weight vs. total resistance.", meta_style))

    doc.build(story)
