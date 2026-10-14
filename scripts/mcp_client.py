"""Call the assets MCP endpoint, checking the connected project before any requested tool."""
import asyncio
import json
from pathlib import Path
import sys

from fastmcp import Client

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:9082/mcp"


async def main():
    async with Client(URL) as client:
        info = await client.call_tool("godot_get_server_info", {})
        data = info.structured_content
        if not data:
            raise SystemExit("MCP returned no structured identity; refusing further commands.")
        bridge = data["bridge"]
        actual = bridge.get("project_path")
        if not bridge.get("connected") or not actual or Path(actual).resolve() != ROOT:
            raise SystemExit(f"Wrong or disconnected editor: {actual!r}; refusing further commands.")
        if len(sys.argv) == 1:
            summary = {key: bridge.get(key) for key in (
                "connected", "url", "godot_version", "project_name", "project_path", "addon_version")}
            print(json.dumps({"server_version": data["version"], "bridge": summary,
                              "active_scene": data["active_scene"]}, indent=2))
        elif sys.argv[1] == "--list":
            print(json.dumps([tool.model_dump() for tool in await client.list_tools()], indent=2))
        else:
            params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
            result = await client.call_tool(sys.argv[1], params)
            if result.structured_content is not None:
                print(json.dumps(result.structured_content, indent=2))
            else:
                for content in result.content:
                    if hasattr(content, "text"):
                        print(content.text)


if __name__ == "__main__":
    asyncio.run(main())
