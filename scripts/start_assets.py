"""Start the isolated assets MCP server and Godot editor. Never touches the game editor."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
GODOT = os.environ.get("ASSETS_GODOT_BIN", "/Applications/Godot.app/Contents/MacOS/Godot")
BRIDGE_PORT = 9081
HTTP_PORT = 9082


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def main():
    for port in (BRIDGE_PORT, HTTP_PORT):
        if listening(port):
            raise SystemExit(f"Port {port} is already occupied; refusing to start another session.")
    uvx = shutil.which("uvx")
    if not uvx or not Path(GODOT).is_file():
        raise SystemExit("Requires uvx and Godot. Set ASSETS_GODOT_BIN if Godot is installed elsewhere.")
    LOCAL.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update({
        "GODOT_MCP_BRIDGE_URL": f"ws://127.0.0.1:{BRIDGE_PORT}",
        "GODOT_MCP_TRANSPORT": "http",
        "GODOT_MCP_HTTP_HOST": "127.0.0.1",
        "GODOT_MCP_HTTP_PORT": str(HTTP_PORT),
        "GODOT_MCP_PROJECT_DIR": str(ROOT),
        "GODOT_MCP_GODOT_BIN": GODOT,
        "GODOT_MCP_AUTO_REFRESH": "true",
    })
    with (LOCAL / "mcp.log").open("a") as log:
        server = subprocess.Popen(
            [uvx, "--offline", "--from", "godot-editor-mcp==2026.10.12", "godot-editor-mcp"],
            cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
    deadline = time.monotonic() + 20
    while not (listening(BRIDGE_PORT) and listening(HTTP_PORT)):
        if server.poll() is not None or time.monotonic() > deadline:
            if server.poll() is None:
                server.terminate()
            raise SystemExit("Assets MCP did not start. See .local/mcp.log.")
        time.sleep(0.2)
    with (LOCAL / "editor.log").open("a") as log:
        editor = subprocess.Popen(
            [GODOT, "--editor", "--path", str(ROOT), "res://previews/asset_stage.tscn"],
            cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
    state = {"project": str(ROOT), "server_pid": server.pid, "editor_pid": editor.pid,
             "bridge_url": env["GODOT_MCP_BRIDGE_URL"],
             "mcp_url": f"http://127.0.0.1:{HTTP_PORT}/mcp"}
    (LOCAL / "session.json").write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
