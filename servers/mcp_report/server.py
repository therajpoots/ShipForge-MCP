import asyncio
import json
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from pdf_generator import build_pdf_report, generate_pareto_plot
from geometry_exporter import export_hull_to_iges

app = Server("mcp-report")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="generate_design_report",
            description="Generate a publication-quality design report PDF with design metrics, DNV status, and charts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "design_id": {"type": "string", "description": "Optimized design ID (e.g. 'SF-150-OPT')"},
                    "design_data": {
                        "type": "object",
                        "description": "JSON object containing hull dimensions, CFD results, stress, and fatigue data"
                    },
                    "population": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of design states explored during optimization (for Pareto plotting)"
                    }
                },
                "required": ["design_id", "design_data"]
            }
        ),
        Tool(
            name="export_to_iges",
            description="Convert and export a ship hull STL mesh to a standard CAD IGES curve file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hull_mesh_path": {"type": "string", "description": "Absolute path to the hull STL mesh"}
                },
                "required": ["hull_mesh_path"]
            }
        ),
        Tool(
            name="plot_pareto_front",
            description="Generate and save a Pareto front visualization comparing drag vs. structural weight.",
            inputSchema={
                "type": "object",
                "properties": {
                    "design_population": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of explored designs, containing 'weight_kg_m2' and 'resistance_kN'"
                    },
                    "output_image_path": {"type": "string", "description": "Path where the PNG plot will be saved"}
                },
                "required": ["design_population", "output_image_path"]
            }
        ),
        Tool(
            name="export_audit_log",
            description="Dump the agent's complete session history log into a formatted JSON audit trail.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Unique session identifier"},
                    "session_log": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of agent reasoning logs and tool calls"
                    }
                },
                "required": ["session_id", "session_log"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    working_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(working_dir, exist_ok=True)
    
    try:
        if name == "generate_design_report":
            design_id = arguments["design_id"]
            design_data = arguments["design_data"]
            population = arguments.get("population", [])
            
            pdf_path = os.path.join(working_dir, f"report_{design_id}.pdf")
            build_pdf_report(design_data, population, pdf_path)
            
            result = {
                "report_pdf_path": pdf_path,
                "details": f"Design report built successfully at '{pdf_path}'."
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "export_to_iges":
            mesh_path = arguments["hull_mesh_path"]
            iges_path = export_hull_to_iges(mesh_path)
            
            result = {
                "iges_file_path": iges_path,
                "details": f"NURBS line geometry successfully exported to '{iges_path}'."
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "plot_pareto_front":
            population = arguments["design_population"]
            out_path = arguments["output_image_path"]
            
            generate_pareto_plot(population, out_path)
            result = {
                "pareto_plot_path": out_path,
                "details": f"Pareto plot image saved successfully at '{out_path}'."
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "export_audit_log":
            session_id = arguments["session_id"]
            session_log = arguments["session_log"]
            
            audit_path = os.path.join(working_dir, f"audit_log_{session_id}.json")
            with open(audit_path, "w") as f:
                json.dump(session_log, f, indent=2)
                
            result = {
                "audit_log_path": audit_path,
                "details": f"Session audit trail dumped to '{audit_path}'."
            }
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
