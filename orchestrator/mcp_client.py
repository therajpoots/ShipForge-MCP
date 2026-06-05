import asyncio
import json
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

# Add workspace to path
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE not in sys.path:
    sys.path.append(WORKSPACE)

# Mapping server names to module launch paths
SERVER_MODULES = {
    "cfd": "servers.mcp_hull_cfd.server",
    "material": "servers.mcp_material_db.server",
    "rule": "servers.mcp_rule_engine.server",
    "fea": "servers.mcp_structural_fea.server",
    "ml": "servers.mcp_fatigue_ml.server",
    "report": "servers.mcp_report.server"
}

class MultiServerClient:
    def __init__(self):
        self.sessions = {}
        self.exit_stack = AsyncExitStack()
        self.tools_map = {} # tool_name -> server_name

    async def start_server(self, name: str, module_path: str):
        print(f"Connecting to MCP Server '{name}' ({module_path})...")
        
        # Setup environment
        env = os.environ.copy()
        server_dir = os.path.join(WORKSPACE, *module_path.split('.')[:-1])
        env["PYTHONPATH"] = f"{server_dir}{os.pathsep}{WORKSPACE}"
        
        # Launch python module as an MCP server
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", module_path],
            env=env
        )
        
        # Connect using SDK stdio client
        read_stream, write_stream = await self.exit_stack.enter_async_context(stdio_client(params))
        session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        
        # Initialize session
        await session.initialize()
        self.sessions[name] = session
        
        # Retrieve and map tools
        tools_list = await session.list_tools()
        # tools_list is a ListToolsResult object containing a list of Tool objects
        for tool in tools_list.tools:
            # Prefix tool call or map directly
            self.tools_map[tool.name] = name
            
        print(f"Server '{name}' initialized with {len(tools_list.tools)} tools.")

    async def connect_all(self):
        """
        Launches all 6 MCP servers in parallel.
        """
        tasks = []
        for name, module in SERVER_MODULES.items():
            tasks.append(self.start_server(name, module))
        await asyncio.gather(*tasks)
        print("All 6 MCP servers successfully connected to Orchestrator client.")

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        Routes tool calls to the appropriate MCP server based on the tool registry.
        """
        server_name = self.tools_map.get(tool_name)
        if not server_name:
            raise ValueError(f"Tool '{tool_name}' is not registered to any active MCP server.")
            
        session = self.sessions[server_name]
        
        # Call tool via Session
        result = await session.call_tool(tool_name, arguments)
        
        # Parse TextContent results
        if not result.content or len(result.content) == 0:
            return {}
            
        text = result.content[0].text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_text": text}

    async def close(self):
        """
        Gracefully terminates all child processes and closes sessions.
        """
        try:
            await self.exit_stack.aclose()
        except Exception:
            pass
        print("All MCP server connections closed.")
