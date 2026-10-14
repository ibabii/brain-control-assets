"""Build the console control GLBs: Blender -b --factory-startup --python scripts/cockpit_v2/build_controls.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import controls  # noqa: E402

print('CONTROLS_BUILT ' + json.dumps(controls.build_all()))
