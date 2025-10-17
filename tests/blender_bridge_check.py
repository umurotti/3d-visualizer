"""Run inside Blender to verify bridge keyframes/timeline."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bpy
from visualizer3d.blender_client import BlenderSceneBridge

bridge = BlenderSceneBridge()

scene_payload = {
    "meshes": [
        {
            "mesh": {"vertices": [], "faces": []},
            "color": "#f8b400",
            "step": 3,
            "label": "test_mesh",
        }
    ],
    "point_clouds": [],
    "frustums": [],
    "axes": [],
    "add_global_axes": False,
    "total_steps": 3,
}

bridge._apply_scene(scene_payload)

scene = bpy.context.scene
obj = bridge._mesh_cache["test_mesh"]
print("frame_start", scene.frame_start)
print("frame_end", scene.frame_end)
print("frame_current", scene.frame_current)
if obj.animation_data and obj.animation_data.action:
    data = {}
    for fcurve in obj.animation_data.action.fcurves:
        keyframes = [kp.co[0] for kp in fcurve.keyframe_points]
        data[fcurve.data_path] = keyframes
    print("keyframes", data)
else:
    print("keyframes", {})
