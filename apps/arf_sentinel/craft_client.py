"""
Async MCP client wrapper for CRAFT.

Encapsulates the JSON‑RPC calls that interact with the CRAFT MCP server.
Each method corresponds to a tool exposed by the server (search_schema,
get_schema, generate_sql, execute_query, etc.).

The client is designed to be used inside an async context manager:

    async with authenticate() as http_client:
        client = CraftMCPClient(http_client)
        tools = await client.list_tools()
"""

import json
from typing import Any, Dict, List
from .craft_auth import authenticate


class CraftMCPClient:
    """
    Wraps raw JSON‑RPC calls into named methods.

    Parameters
    ----------
    client : httpx.AsyncClient
        An authenticated async HTTPX client (usually obtained from
        `craft_auth.authenticate()`).
    """

    def __init__(self, client):
        self.client = client

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Retrieve the list of available MCP tools from the server.

        Returns
        -------
        list of dict
            Each dict contains the tool name, description, and parameters.
        """
        response = await self.client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        )
        return response.json()["result"]["tools"]

    async def search_schema(self, query: str) -> Any:
        """
        Search the CRAFT schema with a natural‑language query.

        Parameters
        ----------
        query : str
            A description of the tables or columns to find.

        Returns
        -------
        The server response (usually a dict containing matching schema items).
        """
        return await self._call_tool("search_schema", {"query": query})

    async def get_schema(self, table: str) -> Any:
        """
        Retrieve detailed schema information for a specific table.

        Parameters
        ----------
        table : str
            The name of the table (e.g., 'GITHUB_REPOS').

        Returns
        -------
        The server response containing column names, types, and metadata.
        """
        return await self._call_tool("get_schema", {"table": table})

    async def generate_sql(self, prompt: str) -> Any:
        """
        Generate an analytical SQL query from a natural‑language prompt.

        Parameters
        ----------
        prompt : str
            A description of the desired data (e.g., "list all repos that
            depend on urllib3").

        Returns
        -------
        The server response containing the generated SQL string.
        """
        return await self._call_tool("generate_sql", {"prompt": prompt})

    async def execute_query(self, sql: str) -> Any:
        """
        Execute a SQL query against the CRAFT‑connected database.

        Parameters
        ----------
        sql : str
            A valid SQL statement.

        Returns
        -------
        The query result (typically a list of rows or a paginated response).
        """
        return await self._call_tool("execute_query", {"sql": sql})

    async def _call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """
        Low‑level JSON‑RPC call to invoke a named MCP tool.

        Parameters
        ----------
        name : str
            The tool name (e.g., 'search_schema').
        args : dict
            The tool arguments.

        Returns
        -------
        The decoded JSON response from the server.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": args},
            "id": 1,
        }
        resp = await self.client.post("/mcp", json=payload)
        return resp.json()
