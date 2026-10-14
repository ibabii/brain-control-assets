"""Use Blender MCP now, with a workspace identity check before requested tools."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client as _stdio_client
from contextlib import asynccontextmanager

ROOT = Path(__file__).resolve().parents[1]
USER_PROMPT = "blender 5.2.2 is installed. install the mcp and configure everything, then confirm what you are ready"


@asynccontextmanager
async def stdio_client(server):
    with (ROOT / ".local/blender_mcp.log").open("a") as errlog:
        async with _stdio_client(server, errlog=errlog) as streams:
            yield streams


def text_result(result):
    return "\n".join(item.text for item in result.content if hasattr(item, "text"))


async def main():
    env = os.environ.copy()
    env.update({"BLENDER_HOST": "127.0.0.1", "BLENDER_PORT": "9876",
                "DISABLE_TELEMETRY": "true", "BLENDER_MCP_SAFE_MODE": "1"})
    server = StdioServerParameters(
        command=shutil.which("uvx") or "/opt/homebrew/bin/uvx",
        args=["--offline", "--python", "3.11", "--from", "mcp-for-blender==2.1.9", "mcp-for-blender"],
        env=env,
    )
    async with stdio_client(server) as (reader, writer):
        async with ClientSession(reader, writer) as client:
            await client.initialize()
            identity = await client.call_tool("execute_blender_code", {
                "code": "import bpy, json\nprint(json.dumps({'workspace': bpy.context.scene.get('brain_control_assets_root'), 'file': bpy.data.filepath, 'version': bpy.app.version_string, 'port': bpy.context.scene.blendermcp_port}))",
                "user_prompt": USER_PROMPT,
            })
            identity_text = text_result(identity)
            if "Code executed successfully:" not in identity_text:
                raise SystemExit(identity_text)
            data = json.loads(identity_text.split("Code executed successfully:", 1)[1].strip())
            if data.get("workspace") != str(ROOT) or data.get("port") != 9876:
                raise SystemExit(f"Wrong Blender workspace: {data}; refusing further commands.")
            if len(sys.argv) == 1:
                print(json.dumps(data, indent=2))
            elif sys.argv[1] == "--list":
                result = await client.list_tools()
                print(json.dumps([tool.model_dump() for tool in result.tools], indent=2))
            else:
                params = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else {}
                if sys.argv[1] in ("execute_blender_code", "get_scene_info", "look"):
                    params.setdefault("user_prompt", USER_PROMPT)
                result = await client.call_tool(sys.argv[1], params)
                output = text_result(result)
                print(output)
                for index, content in enumerate(result.content):
                    if getattr(content, "type", "") == "image":
                        import base64
                        path = ROOT / ".local" / f"blender-{sys.argv[1]}-{index}.png"
                        path.write_bytes(base64.b64decode(content.data))
                        print("IMAGE_SAVED", str(path))
                if result.isError or output.startswith(("Error", "Rejected by safe mode")):
                    raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
