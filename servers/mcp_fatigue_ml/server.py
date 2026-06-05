import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from surrogate_model import (
    predict_fatigue_surrogate,
    estimate_hotspot_stress
)
from weld_classifier import classify_weld_defect

app = Server("mcp-fatigue-ml")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="predict_fatigue_life",
            description="Use a surrogate machine learning model (GBR) to predict fatigue cycles to failure.",
            inputSchema={
                "type": "object",
                "properties": {
                    "stress_range": {"type": "number", "description": "Stress range range in MPa"},
                    "material_id": {"type": "string", "description": "Material ID (e.g. 'NV-AH36')"},
                    "R_ratio": {"type": "number", "description": "Stress ratio R (default -1.0)"},
                    "environment": {"type": "string", "enum": ["air", "seawater", "seawater_cp"], "description": "Corrosion environment"}
                },
                "required": ["stress_range", "material_id", "environment"]
            }
        ),
        Tool(
            name="predict_hotspot_stress",
            description="Predict hotspot stress factor (Ks) and hotspot stress based on joint geometry.",
            inputSchema={
                "type": "object",
                "properties": {
                    "geometry_params": {
                        "type": "object",
                        "properties": {
                            "thickness_mm": {"type": "number", "description": "Plate thickness (mm)"},
                            "weld_angle_deg": {"type": "number", "description": "Weld reinforcement angle in degrees"},
                            "misalignment_mm": {"type": "number", "description": "Joint misalignment offset in mm"}
                        },
                        "required": ["thickness_mm", "weld_angle_deg", "misalignment_mm"]
                    },
                    "nominal_stress_MPa": {"type": "number", "description": "Nominal stress in MPa"}
                },
                "required": ["geometry_params", "nominal_stress_MPa"]
            }
        ),
        Tool(
            name="classify_weld_quality",
            description="Classify weld quality defect from NDT X-ray radiograph and return weld class.",
            inputSchema={
                "type": "object",
                "properties": {
                    "weld_image_path": {"type": "string", "description": "Absolute path to the NDT X-ray radiograph image file"}
                },
                "required": ["weld_image_path"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "predict_fatigue_life":
            s_range = arguments["stress_range"]
            mat_id = arguments["material_id"]
            r_ratio = arguments.get("R_ratio", -1.0)
            env = arguments["environment"]
            
            result = predict_fatigue_surrogate(s_range, mat_id, r_ratio, env)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "predict_hotspot_stress":
            geom = arguments["geometry_params"]
            nominal_stress = arguments["nominal_stress_MPa"]
            
            result = estimate_hotspot_stress(geom, nominal_stress)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "classify_weld_quality":
            image_path = arguments["weld_image_path"]
            
            result = classify_weld_defect(image_path)
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
