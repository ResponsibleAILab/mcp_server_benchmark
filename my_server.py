import mcp
from mcp.server.fastmcp import FastMCP

# Step 1: Create the MCP server
mcp = FastMCP("Mike_MCP_Server")

# Step 2: Add a test tool
@mcp.tool()
def web_search(input_data: dict) -> dict:
    query = input_data.get("query")
    if not query:
        return {"error": "Missing query"}
    return {"summary": f"Fake result for: {query}"}

# Step 3: Run the actual FastAPI app behind FastMCP
if __name__ == "__main__":
    print("Running FastMCP via uvicorn on http://127.0.0.1:8000")
    mcp.run()