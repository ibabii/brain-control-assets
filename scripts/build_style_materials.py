"""Generate Godot starter materials from the authoritative sRGB palette."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "materials/warm_ceramic_v1"
palette = json.loads((DIRECTORY / "palette.json").read_text())
for color in palette["colors"]:
    rgb = [int(color["hex"][i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    profile = palette["profiles"][color["default_profile"]]
    text = (
        '[gd_resource type="StandardMaterial3D" format=3]\n\n'
        '[resource]\n'
        f'resource_name = "WC1_{color["id"]}_{color["default_profile"]}"\n'
        f'albedo_color = Color({rgb[0]:.8f}, {rgb[1]:.8f}, {rgb[2]:.8f}, 1)\n'
        f'roughness = {profile["roughness"]}\n'
        f'metallic = {profile["metallic"]}\n'
    )
    (DIRECTORY / (color["id"] + ".tres")).write_text(text)
print(f"Generated {len(palette['colors'])} materials for {palette['style_id']}")
