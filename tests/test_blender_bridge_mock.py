"""
Lightweight sanity checks for the BlenderSceneBridge without requiring Blender.

These tests stub out the ``bpy`` and ``mathutils`` modules so that we can load
the bridge and exercise its keyframe/timeline logic from a stock CPython
interpreter.
"""

import sys
import types
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Stub modules that emulate the tiny slice of Blender APIs the bridge touches.


class FakeTimerRegistry:
    def __init__(self):
        self.registered = []

    def register(self, func, first_interval=0.0):
        self.registered.append((func, first_interval))

    def unregister(self, func):
        self.registered = [entry for entry in self.registered if entry[0] != func]


@dataclass
class FakeScene:
    frame_start: int = 0
    frame_end: int = 0
    frame_current: int = 0

    @dataclass
    class _CollectionChildren:
        linked: list = field(default_factory=list)

        def link(self, collection):
            self.linked.append(collection)

    @dataclass
    class _RootCollection:
        children: "FakeScene._CollectionChildren" = field(default_factory=lambda: FakeScene._CollectionChildren())

    collection: _RootCollection = field(default_factory=_RootCollection)


class FakeBpyModule(types.ModuleType):
    def __init__(self):
        super().__init__("bpy")
        self.app = types.SimpleNamespace(timers=FakeTimerRegistry())
        self.context = types.SimpleNamespace(scene=FakeScene())
        self.data = types.SimpleNamespace(
            collections={},
            meshes=types.SimpleNamespace(),
            objects=types.SimpleNamespace(),
        )


class FakeMatrix:
    def __init__(self, rows):
        self.rows = tuple(tuple(float(v) for v in row) for row in rows)

    @staticmethod
    def Identity(size):
        rows = []
        for r in range(size):
            row = [0.0] * size
            row[r] = 1.0
            rows.append(row)
        return FakeMatrix(rows)

    def __iter__(self):
        return iter(self.rows)


class FakeMathutils(types.ModuleType):
    def __init__(self):
        super().__init__("mathutils")
        self.Matrix = FakeMatrix


sys.modules.setdefault("bpy", FakeBpyModule())
sys.modules.setdefault("mathutils", FakeMathutils())


# Import after stubbing.
from visualizer3d.blender_client import BlenderSceneBridge  # noqa: E402  pylint: disable=wrong-import-position


# ---------------------------------------------------------------------------
# Helper fakes used inside the test harness.


class FakeObject(dict):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.keyframes = defaultdict(list)
        self.hide_viewport = False
        self.hide_render = False
        self.display_type = "TEXTURED"
        self.data = types.SimpleNamespace(materials=[])
        self.matrix_world = FakeMatrix.Identity(4)
        self.rotation_mode = "XYZ"

    def keyframe_insert(self, data_path, frame):
        self.keyframes[data_path].append(frame)


class FakeCollectionObjects(list):
    def link(self, obj):
        self.append(obj)


class FakeBridge(BlenderSceneBridge):
    """Subclass that bypasses Blender-specific object creation."""

    def __init__(self):
        # Do not call super().__init__.
        self.host = "http://stub"
        self.collection = types.SimpleNamespace(objects=FakeCollectionObjects())
        self._mesh_cache = {}
        self._point_cloud_cache = {}
        self._frustum_cache = {}
        self._axis_cache = {}
        self._materials = {}
        self._scene_queue = []
        self._lock = types.SimpleNamespace(__enter__=lambda self: None, __exit__=lambda self, *exc: None)
        self._poll_thread = None
        self._stop_event = types.SimpleNamespace(is_set=lambda: False, wait=lambda interval: None, set=lambda: None)
        self._pending_step = None
        self._poll_interval = 1.0
        self._timer_handle = None
        self._visibility_cache = {}
        self._latest_step = 0

    # --- creation helpers rewritten to produce fake objects ----
    def _create_mesh_object(self, name):
        return FakeObject(name)

    _create_point_cloud_object = _create_mesh_object
    _create_frustum_object = _create_mesh_object
    _create_axis_object = _create_mesh_object

    def _update_mesh_geometry(self, obj, vertices, faces):
        obj.data.vertices = vertices
        obj.data.faces = faces

    def _update_point_cloud_geometry(self, obj, points):
        obj.data.points = points

    def _update_frustum_geometry(self, obj, vertices, edges):
        obj.data.vertices = vertices
        obj.data.edges = edges

    def _apply_material(self, obj, color, emission_strength=0.0):
        obj.data.materials.append((color, emission_strength))

    _apply_wire_material = _apply_material

    def _build_frustum(self, entry):
        return [], []


# ---------------------------------------------------------------------------
# Actual tests


def test_keyframes_and_timeline():
    bridge = FakeBridge()
    scene_stub = sys.modules["bpy"].context.scene
    scene_stub.frame_start = 0
    scene_stub.frame_end = 0
    scene_stub.frame_current = 0

    scene_payload = {
        "meshes": [
            {
                "mesh": {"vertices": [], "faces": []},
                "color": "#f8b400",
                "step": 5,
                "label": "bunny_mesh",
            }
        ],
        "point_clouds": [],
        "frustums": [],
        "axes": [],
        "add_global_axes": False,
        "total_steps": 5,
    }

    bridge._apply_scene(scene_payload)

    mesh_obj = bridge._mesh_cache["bunny_mesh"]
    assert mesh_obj.keyframes["hide_viewport"] == [4, 5, 6]
    assert mesh_obj.keyframes["hide_render"] == [4, 5, 6]
    assert scene_stub.frame_start == 0
    assert scene_stub.frame_end == 6  # total_steps + 1
    assert scene_stub.frame_current == 5
    assert bridge._latest_step == 5


def run():
    test_keyframes_and_timeline()
    print("Blender bridge keyframe/timeline checks passed.")


if __name__ == "__main__":
    run()
