import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from dnv_part3_ch1 import (
    calculate_design_pressure,
    check_plate_thickness_dnv,
    check_section_modulus_dnv,
    check_buckling_dnv
)
from dnv_stability import check_intact_stability

app = Server("mcp-rule-engine")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_design_pressure",
            description="Calculate bottom, side shell, or deck hydrostatic + dynamic design pressure per DNV.",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "enum": ["bottom", "side_shell", "deck", "bulkhead"]},
                    "Lpp": {"type": "number", "description": "Length between perpendiculars (m)"},
                    "draft": {"type": "number", "description": "Moulded design draft (m)"},
                    "beam": {"type": "number", "description": "Moulded beam (m)"},
                    "speed_knots": {"type": "number", "description": "Vessel service speed (knots)"},
                    "sea_state_Hs": {"type": "number", "description": "Significant wave height Hs in m (default 6.0)"}
                },
                "required": ["location", "Lpp", "draft", "beam", "speed_knots"]
            }
        ),
        Tool(
            name="check_plate_thickness",
            description="Check if plate thickness meets DNV Rules for Ships Part 3 Chapter 1 local pressure bending.",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "enum": ["bottom", "side_shell", "deck", "bulkhead"]},
                    "material_id": {"type": "string", "description": "Material ID (e.g., 'NV-AH36')"},
                    "design_pressure_kPa": {"type": "number", "description": "Design pressure on plate (kPa)"},
                    "plate_span_m": {"type": "number", "description": "Span of plate panel between frames (m)"},
                    "stiffener_spacing_m": {"type": "number", "description": "Spacing of secondary stiffeners (m)"},
                    "actual_thickness_mm": {"type": "number", "description": "Actual plate thickness to test (mm)"},
                    "corrosion_allowance_mm": {"type": "number", "description": "Corrosion margin allowance (default 1.5mm)"}
                },
                "required": ["location", "material_id", "design_pressure_kPa", "plate_span_m", "stiffener_spacing_m", "actual_thickness_mm"]
            }
        ),
        Tool(
            name="check_section_modulus",
            description="Check if secondary stiffener section modulus complies with DNV Rules.",
            inputSchema={
                "type": "object",
                "properties": {
                    "material_id": {"type": "string", "description": "Material ID (e.g., 'NV-AH36')"},
                    "design_pressure_kPa": {"type": "number", "description": "Design pressure on stiffener (kPa)"},
                    "stiffener_spacing_m": {"type": "number", "description": "Spacing between stiffeners (m)"},
                    "span_m": {"type": "number", "description": "Unsupported span length of stiffener (m)"},
                    "actual_section_modulus_cm3": {"type": "number", "description": "Actual elastic section modulus (cm^3)"}
                },
                "required": ["material_id", "design_pressure_kPa", "stiffener_spacing_m", "span_m", "actual_section_modulus_cm3"]
            }
        ),
        Tool(
            name="check_buckling",
            description="Verify plate panel under compression against DNV buckling requirements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "material_id": {"type": "string", "description": "Material ID (e.g. 'NV-AH36')"},
                    "youngs_modulus_GPa": {"type": "number", "description": "Young's modulus of material"},
                    "yield_strength_MPa": {"type": "number", "description": "Yield strength of material"},
                    "plate_width_m": {"type": "number", "description": "Stiffener spacing / panel width (m)"},
                    "plate_length_m": {"type": "number", "description": "Frame spacing / panel length (m)"},
                    "thickness_mm": {"type": "number", "description": "Plate thickness (mm)"},
                    "actual_compressive_stress_MPa": {"type": "number", "description": "Compressive stress in plate panel (MPa)"}
                },
                "required": ["material_id", "youngs_modulus_GPa", "yield_strength_MPa", "plate_width_m", "plate_length_m", "thickness_mm", "actual_compressive_stress_MPa"]
            }
        ),
        Tool(
            name="check_stability",
            description="Check ship intact stability GM against the DNV rule (GM/L > 0.033).",
            inputSchema={
                "type": "object",
                "properties": {
                    "loa": {"type": "number", "description": "Length overall (m)"},
                    "beam": {"type": "number", "description": "Vessel beam (m)"},
                    "draft": {"type": "number", "description": "Vessel draft (m)"},
                    "depth": {"type": "number", "description": "Vessel depth (m)"},
                    "Cb": {"type": "number", "description": "Block coefficient"},
                    "kg_m": {"type": "number", "description": "Optional center of gravity height above keel (m)"}
                },
                "required": ["loa", "beam", "draft", "depth", "Cb"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "get_design_pressure":
            result = calculate_design_pressure(
                location=arguments["location"],
                Lpp=arguments["Lpp"],
                draft=arguments["draft"],
                beam=arguments["beam"],
                speed_knots=arguments["speed_knots"],
                sea_state_Hs=arguments.get("sea_state_Hs", 6.0)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "check_plate_thickness":
            result = check_plate_thickness_dnv(
                location=arguments["location"],
                material_id=arguments["material_id"],
                design_pressure_kPa=arguments["design_pressure_kPa"],
                plate_span_m=arguments["plate_span_m"],
                stiffener_spacing_m=arguments["stiffener_spacing_m"],
                actual_thickness_mm=arguments["actual_thickness_mm"],
                corrosion_allowance_mm=arguments.get("corrosion_allowance_mm", 1.5)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "check_section_modulus":
            result = check_section_modulus_dnv(
                material_id=arguments["material_id"],
                design_pressure_kPa=arguments["design_pressure_kPa"],
                stiffener_spacing_m=arguments["stiffener_spacing_m"],
                span_m=arguments["span_m"],
                actual_section_modulus_cm3=arguments["actual_section_modulus_cm3"]
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "check_buckling":
            result = check_buckling_dnv(
                material_id=arguments["material_id"],
                youngs_modulus_GPa=arguments["youngs_modulus_GPa"],
                yield_strength_MPa=arguments["yield_strength_MPa"],
                plate_width_m=arguments["plate_width_m"],
                plate_length_m=arguments["plate_length_m"],
                thickness_mm=arguments["thickness_mm"],
                actual_compressive_stress_MPa=arguments["actual_compressive_stress_MPa"]
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "check_stability":
            result = check_intact_stability(
                loa=arguments["loa"],
                beam=arguments["beam"],
                draft=arguments["draft"],
                depth=arguments["depth"],
                Cb=arguments["Cb"],
                kg_m=arguments.get("kg_m", None)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        else:
            return [TextContent(type="text", text=f"Error: Tool '{name}' not found.")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error processing tool call: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
