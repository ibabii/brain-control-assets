"""Enable MCP in a new assets Blender process and persist the addon preference."""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
LOCAL.mkdir(exist_ok=True)
bpy.ops.preferences.addon_enable(module="blender_mcp")
bpy.context.preferences.addons["blender_mcp"].preferences.telemetry_consent = False
bpy.context.scene.blendermcp_port = 9876
bpy.context.scene.blendermcp_auto_start_server = True
bpy.context.scene["brain_control_assets_root"] = str(ROOT)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 1.0
bpy.ops.wm.save_userpref()
bpy.ops.wm.save_as_mainfile(filepath=str(LOCAL / "assets_workspace.blend"))
bpy.ops.blendermcp.start_server()
print("ASSETS_BLENDER_READY", str(ROOT), "port=9876", flush=True)
