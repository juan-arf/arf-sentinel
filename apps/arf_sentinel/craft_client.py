import json
from .craft_auth import authenticate

class CraftMCPClient:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def list_tools(self):
        response = await self.client.post("/mcp", json={"jsonrpc": "2.0", "method": "tools/list", "id": 1})
        return response.json()["result"]["tools"]

    async def search_schema(self, query: str):
        return await self._call_tool("search_schema", {"query": query})

    async def get_schema(self, table: str):
        return await self._call_tool("get_schema", {"table": table})

    async def generate_sql(self, prompt: str):
        return await self._call_tool("generate_sql", {"prompt": prompt})

    async def execute_query(self, sql: str):
        return await self._call_tool("execute_query", {"sql": sql})

    async def _call_tool(self, name: str, args: dict):
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": args},
            "id": 1
        }
        resp = await self.client.post("/mcp", json=payload)
        return resp.json()
