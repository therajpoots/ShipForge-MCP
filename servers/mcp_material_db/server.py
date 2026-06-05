import asyncio
import json
import sqlite3
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from database import DB_PATH
from sn_curves import get_fatigue_life
from corrosion_model import compute_corrosion_allowance

app = Server("mcp-material-db")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="query_material",
            description="Query mechanical and physical properties of a shipbuilding material.",
            inputSchema={
                "type": "object",
                "properties": {
                    "material_id": {"type": "string", "description": "Unique material identifier (e.g., 'NV-AH36', 'AL-5083')"},
                },
                "required": ["material_id"]
            }
        ),
        Tool(
            name="get_sn_curve",
            description="Compute cycles to failure (N) under wave-induced cyclic stress using DNV S-N curves.",
            inputSchema={
                "type": "object",
                "properties": {
                    "material_id": {"type": "string", "description": "Material ID (e.g., 'NV-AH36')"},
                    "environment": {"type": "string", "enum": ["air", "seawater", "seawater_cp"], "description": "Operating environment"},
                    "weld_class": {"type": "string", "enum": ["B", "C", "D", "E", "F", "F2", "G", "W"], "description": "Weld category per IIW / DNV rules"},
                    "stress_range_MPa": {"type": "number", "description": "Stress range in MPa"}
                },
                "required": ["material_id", "environment", "weld_class", "stress_range_MPa"]
            }
        ),
        Tool(
            name="get_corrosion_rate",
            description="Predict corrosion degradation in mm for a given environment and design life.",
            inputSchema={
                "type": "object",
                "properties": {
                    "material_id": {"type": "string", "description": "Material ID (e.g., 'NV-A')"},
                    "salinity_ppt": {"type": "number", "description": "Salinity in ppt (default 35.0)"},
                    "temp_C": {"type": "number", "description": "Average seawater temperature in C (default 15.0)"},
                    "exposure_years": {"type": "number", "description": "Exposure duration/service life in years (default 25.0)"},
                    "coating_quality": {"type": "string", "enum": ["good", "fair", "poor", "none"], "description": "Quality of corrosion protection coating"},
                    "cp_applied": {"type": "boolean", "description": "Is active Cathodic Protection applied?"}
                },
                "required": ["material_id"]
            }
        ),
        Tool(
            name="compare_materials",
            description="Rank and compare a list of materials for a specific structural design objective.",
            inputSchema={
                "type": "object",
                "properties": {
                    "material_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of material IDs to compare"
                    },
                    "objective": {
                        "type": "string",
                        "enum": ["specific_strength", "minimum_weight", "minimum_cost_estimate"],
                        "description": "Optimization criteria"
                    }
                },
                "required": ["material_ids", "objective"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "query_material":
            material_id = arguments["material_id"]
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE material_id = ?", (material_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return [TextContent(type="text", text=f"Error: Material '{material_id}' not found in database.")]
            
            data = dict(row)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
            
        elif name == "get_sn_curve":
            material_id = arguments["material_id"]
            environment = arguments["environment"]
            weld_class = arguments["weld_class"]
            stress_range = arguments["stress_range_MPa"]
            
            result = get_fatigue_life(material_id, environment, weld_class, stress_range)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "get_corrosion_rate":
            material_id = arguments["material_id"]
            
            # Get material class
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT class FROM materials WHERE material_id = ?", (material_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return [TextContent(type="text", text=f"Error: Material '{material_id}' not found.")]
            
            mat_class = row[0]
            
            salinity = arguments.get("salinity_ppt", 35.0)
            temp = arguments.get("temp_C", 15.0)
            years = arguments.get("exposure_years", 25.0)
            coating = arguments.get("coating_quality", "good")
            cp = arguments.get("cp_applied", True)
            
            result = compute_corrosion_allowance(mat_class, salinity, temp, years, coating, cp)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        elif name == "compare_materials":
            material_ids = arguments["material_ids"]
            objective = arguments["objective"]
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            placeholders = ",".join("?" for _ in material_ids)
            cursor.execute(f"SELECT * FROM materials WHERE material_id IN ({placeholders})", material_ids)
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                d = dict(row)
                # Compute objective metrics
                # Specific Strength = Yield Strength / Density
                # Minimum Weight = density / Yield Strength (proxy)
                density = d["density_kg_m3"]
                fy = d["yield_strength_MPa"]
                
                spec_strength = fy / (density / 1000.0) # MPa per g/cm^3
                weight_index = density / fy
                
                # Mock cost estimator (composites high, steel low, alum med)
                cost_factors = {"steel": 1.0, "aluminium": 3.0, "frp": 5.0, "cfrp": 15.0}
                cost_est = cost_factors.get(d["class"], 1.0) * density
                
                d["specific_strength"] = round(spec_strength, 2)
                d["weight_index"] = round(weight_index, 2)
                d["cost_index"] = round(cost_est, 2)
                results.append(d)
                
            if objective == "specific_strength":
                results.sort(key=lambda x: x["specific_strength"], reverse=True)
            elif objective == "minimum_weight":
                results.sort(key=lambda x: x["weight_index"])
            elif objective == "minimum_cost_estimate":
                results.sort(key=lambda x: x["cost_index"])
                
            return [TextContent(type="text", text=json.dumps(results, indent=2))]
            
        else:
            return [TextContent(type="text", text=f"Error: Tool '{name}' not found.")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error processing tool call: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
