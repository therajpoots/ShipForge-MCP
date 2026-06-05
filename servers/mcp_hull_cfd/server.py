import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from hull_generator import generate_series60_hull
from cfd_runner import (
    run_resistance_cfd,
    run_seakeeping_cfd,
    calculate_wake_fraction
)

app = Server("mcp-hull-cfd")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="generate_hull_mesh",
            description="Generate a parametric 3D Series 60 ship hull mesh (STL) and return its wetted area.",
            inputSchema={
                "type": "object",
                "properties": {
                    "loa": {"type": "number", "description": "Length overall (m)"},
                    "beam": {"type": "number", "description": "Moulded beam (m)"},
                    "draft": {"type": "number", "description": "Design draft (m)"},
                    "Cb": {"type": "number", "description": "Block coefficient (0.55 - 0.85)"},
                    "bow_type": {"type": "string", "enum": ["bulbous", "conventional", "inverted"], "description": "Type of bow shape"}
                },
                "required": ["loa", "beam", "draft", "Cb", "bow_type"]
            }
        ),
        Tool(
            name="run_resistance_simulation",
            description="Run a resistance simulation (simpleFoam or Holtrop-Mennen) and return drag forces.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mesh_path": {"type": "string", "description": "Path to the generated hull STL mesh"},
                    "speed_knots": {"type": "number", "description": "Vessel service speed in knots"},
                    "water_temp": {"type": "number", "description": "Water temperature in C (default 15.0)"}
                },
                "required": ["mesh_path", "speed_knots"]
            }
        ),
        Tool(
            name="run_seakeeping_simulation",
            description="Run a sea state ship motion simulation and return heave/pitch RAOs and motion sickness index.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mesh_path": {"type": "string", "description": "Path to the generated hull STL mesh"},
                    "sea_state": {"type": "number", "description": "Significant wave height Hs in meters"},
                    "heading": {"type": "number", "description": "Heading angle in degrees (default 180.0 for head seas)"}
                },
                "required": ["mesh_path", "sea_state"]
            }
        ),
        Tool(
            name="get_wake_fraction",
            description="Calculate wake fraction, thrust deduction, and hull efficiency at propeller disk.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mesh_path": {"type": "string", "description": "Path to the generated hull STL mesh"},
                    "propeller_diameter": {"type": "number", "description": "Propeller diameter in meters"}
                },
                "required": ["mesh_path", "propeller_diameter"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "generate_hull_mesh":
            mesh_path, s_area = generate_series60_hull(
                loa=arguments["loa"],
                beam=arguments["beam"],
                draft=arguments["draft"],
                Cb=arguments["Cb"],
                bow_type=arguments["bow_type"]
            )
            result = {
                "mesh_path": mesh_path,
                "hull_surface_area_m2": s_area
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "run_resistance_simulation":
            mesh_path = arguments["mesh_path"]
            speed_knots = arguments["speed_knots"]
            water_temp = arguments.get("water_temp", 15.0)
            
            result = run_resistance_cfd(mesh_path, speed_knots, water_temp)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "run_seakeeping_simulation":
            mesh_path = arguments["mesh_path"]
            sea_state = arguments["sea_state"]
            heading = arguments.get("heading", 180.0)
            
            result = run_seakeeping_cfd(mesh_path, sea_state, heading)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "get_wake_fraction":
            mesh_path = arguments["mesh_path"]
            prop_dia = arguments["propeller_diameter"]
            
            result = calculate_wake_fraction(mesh_path, prop_dia)
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
