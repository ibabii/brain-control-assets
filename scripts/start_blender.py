"""Launch an isolated assets Blender workspace. Existing Blender processes are left alone."""
import json
import os
from pathlib import Path
import socket
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
BLENDER = os.environ.get("ASSETS_BLENDER_BIN", "/Applications/Blender.app/Contents/MacOS/Blender")

try:
    with socket.create_connection(("127.0.0.1", 9876), timeout=0.3):
        raise SystemExit("Port 9876 is occupied; refusing to start a second Blender server.")
except OSError:
    pass

if not Path(BLENDER).is_file():
    raise SystemExit("Blender not found. Set ASSETS_BLENDER_BIN to its executable.")
LOCAL.mkdir(exist_ok=True)
env = os.environ.copy()
env["DISABLE_TELEMETRY"] = "true"
with (LOCAL / "blender.log").open("a") as log:
    process = subprocess.Popen(
        [BLENDER, "--python", str(ROOT / "scripts/blender_bootstrap.py")],
        cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
state = {"pid": process.pid, "project": str(ROOT), "port": 9876}
(LOCAL / "blender_session.json").write_text(json.dumps(state, indent=2) + "\n")
print(json.dumps(state, indent=2))
