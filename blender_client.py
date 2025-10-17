"""
Blender client for the visualizer3d scene API.

This module is meant to be executed inside Blender's Python environment.
It periodically polls a remote visualizer3d Flask server (typically running on
the remote machine) and mirrors meshes, point clouds, frustums, and axes inside
the current Blender scene.

Usage (inside Blender's scripting console or as part of an add-on):

    from visualizer3d import blender_client
    bridge = blender_client.BlenderSceneBridge(host="http://localhost:5000")
    bridge.start_polling(interval=1.0)  # seconds between synchronisation calls

To stop the polling loop:

    bridge.stop_polling()

The bridge keeps all imported objects inside a dedicated collection so it will
not interfere with existing scene content.
"""

from __future__ import annotations

import collections
import threading
from typing import Deque, Dict, Iterable, List, Optional, Set, Tuple

import bpy
import mathutils
import requests


def _read_default_host() -> str:
    """Mirror the behaviour of viewer_client by looking for port.txt."""
    try:
        with open("port.txt", "r", encoding="utf-8") as fp:
            port = fp.read().strip()
    except OSError:
        port = "5000"
    return f"http://localhost:{port}"


def _hex_to_rgb(color: str) -> Tuple[float, float, float]:
    """Convert a hex colour (e.g. '#ff00ff') into linear RGB floats."""
    if not isinstance(color, str) or not color.startswith("#") or len(color) != 7:
        return 0.2, 0.8, 0.2  # default green
    r = int(color[1:3], 16) / 255.0
    g = int(color[3:5], 16) / 255.0
    b = int(color[5:7], 16) / 255.0
    return r, g, b


def _pose_to_matrix(pose: Iterable[Iterable[float]]) -> mathutils.Matrix:
    """Convert a nested iterable into a Blender Matrix."""
    flat = [float(x) for row in pose for x in row]
    if len(flat) != 16:
        raise ValueError("Pose must contain 16 floats.")
    return mathutils.Matrix(((flat[0], flat[1], flat[2], flat[3]),
                             (flat[4], flat[5], flat[6], flat[7]),
                             (flat[8], flat[9], flat[10], flat[11]),
                             (flat[12], flat[13], flat[14], flat[15])))


class BlenderSceneBridge:
    """Synchronise remote visualizer3d scenes into Blender."""

    COLLECTION_NAME = "Visualizer3D Remote Scene"
    _TIMER_INTERVAL = 0.25  # seconds between UI updates

    def __init__(self, host: Optional[str] = None):
        self.host = host or _read_default_host()
        self.collection = self._ensure_collection(self.COLLECTION_NAME)
        self._mesh_cache: Dict[str, bpy.types.Object] = {}
        self._point_cloud_cache: Dict[str, bpy.types.Object] = {}
        self._frustum_cache: Dict[str, bpy.types.Object] = {}
        self._axis_cache: Dict[str, bpy.types.Object] = {}
        self._materials: Dict[str, bpy.types.Material] = {}
        self._scene_queue: Deque[dict] = collections.deque(maxlen=2)
        self._lock = threading.Lock()
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pending_step: Optional[int] = None
        self._poll_interval = 1.0
        self._timer_handle = None
        self._visibility_cache: Dict[str, Set[int]] = {}
        self._latest_step = 0

    # ------------------------------------------------------------------
    # Public API

    def start_polling(self, interval: float = 1.0, step: Optional[int] = None):
        """Start syncing the scene at a fixed interval (seconds)."""
        interval = max(0.1, float(interval))
        with self._lock:
            if self._poll_thread and self._poll_thread.is_alive():
                raise RuntimeError("Polling already running.")
            self._pending_step = step
            self._poll_interval = interval
            self._stop_event.clear()
            self._latest_step = 0

        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        if self._timer_handle is None:
            self._timer_handle = self._process_queue
            bpy.app.timers.register(self._timer_handle, first_interval=self._TIMER_INTERVAL)

        scene = bpy.context.scene
        if scene is not None and scene.frame_start != 0:
            scene.frame_start = 0

        print(f"[Visualizer3D] Started polling {self.host} every {interval}s")

    def stop_polling(self):
        """Stop the polling loop."""
        thread = None
        with self._lock:
            if not self._poll_thread:
                return
            self._stop_event.set()
            thread = self._poll_thread
            self._poll_thread = None

        if thread:
            thread.join(timeout=2.0)

        if self._timer_handle is not None:
            try:
                bpy.app.timers.unregister(self._timer_handle)
            except ValueError:
                pass
            self._timer_handle = None

        print("[Visualizer3D] Stopped polling.")

    def sync(self, step: Optional[int] = None):
        """Fetch the scene state and mirror it into Blender (blocking)."""
        scene = self._fetch_scene(step)
        if scene is not None:
            self._apply_scene(scene)

    # ------------------------------------------------------------------
    # Background polling

    def _poll_loop(self):
        while not self._stop_event.is_set():
            scene = self._fetch_scene(self._pending_step)
            if scene is not None:
                with self._lock:
                    self._scene_queue.append(scene)
            self._stop_event.wait(self._poll_interval)

    def _process_queue(self):
        scene = None
        with self._lock:
            if self._scene_queue:
                scene = self._scene_queue.popleft()
        if scene is not None:
            try:
                self._apply_scene(scene)
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[Visualizer3D] Failed to apply scene: {exc}")

        if self._stop_event.is_set():
            with self._lock:
                empty = not self._scene_queue
            if empty:
                self._timer_handle = None
                return None
        return self._TIMER_INTERVAL

    # ------------------------------------------------------------------
    # Keyframe helpers

    def _ensure_scene_range(self, step: Optional[int]):
        if step is None:
            return
        scene = bpy.context.scene
        if scene is None:
            return
        frame = int(step)
        if frame < scene.frame_start:
            scene.frame_start = frame
        if frame + 1 > scene.frame_end:
            scene.frame_end = frame + 1

    def _keyframe_visibility(self, obj: bpy.types.Object, step: Optional[int], hold_visible: bool = False):
        if step is None:
            return
        step = int(step)
        cache = self._visibility_cache.setdefault(obj.name, set())
        if step in cache:
            return
        cache.add(step)

        frames = []
        frame_before = max(step - 1, 0)
        if frame_before < step:
            frames.append((frame_before, True))
        frames.append((step, False))
        if not hold_visible:
            frames.append((step + 1, True))

        seen = set()
        for frame, hidden in frames:
            if frame in seen:
                continue
            seen.add(frame)
            obj.hide_viewport = hidden
            obj.hide_render = hidden
            obj.keyframe_insert(data_path="hide_viewport", frame=frame)
            obj.keyframe_insert(data_path="hide_render", frame=frame)
            self._ensure_scene_range(frame)

    def _keyframe_transform(self, obj: bpy.types.Object, step: Optional[int]):
        if step is None:
            return
        step = int(step)
        loc, rot, scale = obj.matrix_world.decompose()
        obj.location = loc
        if getattr(obj, "rotation_mode", None) is None:
            obj.rotation_mode = 'XYZ'
        obj.rotation_euler = rot.to_euler(obj.rotation_mode)
        obj.scale = scale
        obj.keyframe_insert(data_path="location", frame=step)
        obj.keyframe_insert(data_path="rotation_euler", frame=step)
        obj.keyframe_insert(data_path="scale", frame=step)
        self._ensure_scene_range(step)
        self._register_step(step)

    def _register_step(self, step: Optional[int]):
        if step is None:
            return
        step = int(step)
        if step > self._latest_step:
            self._latest_step = step

    def _update_timeline_bounds(self):
        scene = bpy.context.scene
        if scene is None:
            return
        end = max(self._latest_step + 1, 1)
        if scene.frame_end != end:
            scene.frame_end = end
        if scene.frame_start != 0:
            scene.frame_start = 0
        if scene.frame_current < self._latest_step:
            scene.frame_current = self._latest_step

    # ------------------------------------------------------------------
    # Networking helpers

    def _fetch_scene(self, step: Optional[int]) -> Optional[dict]:
        url = f"{self.host}/scene"
        params = {"step": step} if step is not None else None
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            print(f"[Visualizer3D] Could not fetch scene: {exc}")
            return None

    # ------------------------------------------------------------------
    # Scene application helpers

    def _apply_scene(self, scene: dict):
        self._sync_meshes(scene.get("meshes", []))
        self._sync_point_clouds(scene.get("point_clouds", []))
        self._sync_frustums(scene.get("frustums", []))
        self._sync_axes(scene.get("axes", []))
        if scene.get("add_global_axes"):
            self._ensure_global_axes()
        total_steps = scene.get("total_steps")
        if isinstance(total_steps, int):
            self._register_step(total_steps)
        self._update_timeline_bounds()
        print("[Visualizer3D] Scene synchronised.")

    def _sync_meshes(self, meshes: List[dict]):
        active = set()
        for idx, entry in enumerate(meshes):
            key = entry.get("label") or f"mesh_{idx}"
            active.add(key)
            obj = self._mesh_cache.get(key)
            if obj is None:
                obj = self._create_mesh_object(key)
                self.collection.objects.link(obj)
                self._mesh_cache[key] = obj
            elif self.collection.objects.get(obj.name) is None:
                self.collection.objects.link(obj)
            mesh_data = entry.get("mesh", {})
            vertices = mesh_data.get("vertices", [])
            faces = mesh_data.get("faces", [])
            self._update_mesh_geometry(obj, vertices, faces)
            color = entry.get("color", "#00ff00")
            self._apply_material(obj, color)
            step_val = entry.get("step")
            obj["visualizer_step"] = step_val if step_val is not None else 0
            obj["visualizer_label"] = entry.get("label", "")
            self._keyframe_visibility(obj, step_val)
            self._register_step(step_val)
        self._remove_stale(self._mesh_cache, active)

    def _sync_point_clouds(self, clouds: List[dict]):
        active = set()
        for idx, entry in enumerate(clouds):
            key = entry.get("label") or f"pointcloud_{idx}"
            active.add(key)
            obj = self._point_cloud_cache.get(key)
            if obj is None:
                obj = self._create_point_cloud_object(key)
                self.collection.objects.link(obj)
                self._point_cloud_cache[key] = obj
            elif self.collection.objects.get(obj.name) is None:
                self.collection.objects.link(obj)
            points = entry.get("points", [])
            self._update_point_cloud_geometry(obj, points)
            color = entry.get("color", "#00ff00")
            self._apply_material(obj, color, emission_strength=3.0)
            step_val = entry.get("step")
            obj["visualizer_step"] = step_val if step_val is not None else 0
            self._keyframe_visibility(obj, step_val)
            self._register_step(step_val)
        self._remove_stale(self._point_cloud_cache, active)

    def _sync_frustums(self, frustums: List[dict]):
        active = set()
        for idx, entry in enumerate(frustums):
            key = entry.get("label") or f"frustum_{idx}"
            active.add(key)
            obj = self._frustum_cache.get(key)
            if obj is None:
                obj = self._create_frustum_object(key)
                self.collection.objects.link(obj)
                self._frustum_cache[key] = obj
            elif self.collection.objects.get(obj.name) is None:
                self.collection.objects.link(obj)
            vertices, edges = self._build_frustum(entry)
            self._update_frustum_geometry(obj, vertices, edges)
            color = entry.get("color", "#00ff00")
            self._apply_wire_material(obj, color)
            pose = entry.get("pose")
            if pose:
                obj.matrix_world = _pose_to_matrix(pose)
                self._keyframe_transform(obj, entry.get("step"))
            step_val = entry.get("step")
            obj["visualizer_step"] = step_val if step_val is not None else 0
            self._keyframe_visibility(obj, step_val)
            self._register_step(step_val)
        self._remove_stale(self._frustum_cache, active)

    def _sync_axes(self, axes: List[dict]):
        active = set()
        for idx, entry in enumerate(axes):
            label = entry.get("label") or f"axis_{idx}"
            active.add(label)
            obj = self._axis_cache.get(label)
            if obj is None:
                obj = self._create_axis_object(label)
                self.collection.objects.link(obj)
                self._axis_cache[label] = obj
            elif self.collection.objects.get(obj.name) is None:
                self.collection.objects.link(obj)
            pose = entry.get("pose")
            if pose:
                obj.matrix_world = _pose_to_matrix(pose)
                self._keyframe_transform(obj, entry.get("step"))
            step_val = entry.get("step")
            obj["visualizer_step"] = step_val if step_val is not None else 0
            self._keyframe_visibility(obj, step_val)
            self._register_step(step_val)
        self._remove_stale(self._axis_cache, active)

    def _ensure_global_axes(self):
        key = "global_axes"
        if key in self._axis_cache:
            return
        obj = self._create_axis_object("GlobalAxes", size=0.6)
        self._axis_cache[key] = obj
        obj.matrix_world = mathutils.Matrix.Identity(4)
        self._keyframe_transform(obj, 0)
        self._keyframe_visibility(obj, 0, hold_visible=True)

    # ------------------------------------------------------------------
    # Creation helpers

    def _ensure_collection(self, name: str) -> bpy.types.Collection:
        collection = bpy.data.collections.get(name)
        if collection is None:
            collection = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(collection)
        return collection

    def _create_mesh_object(self, name: str) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(f"{name}_mesh")
        obj = bpy.data.objects.new(name, mesh)
        obj.display_type = "TEXTURED"
        obj["visualizer_type"] = "mesh"
        return obj

    def _create_point_cloud_object(self, name: str) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(f"{name}_points")
        obj = bpy.data.objects.new(name, mesh)
        obj.display_type = "WIRE"
        obj["visualizer_type"] = "point_cloud"
        return obj

    def _create_frustum_object(self, name: str) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(f"{name}_frustum")
        obj = bpy.data.objects.new(name, mesh)
        obj.display_type = "WIRE"
        obj["visualizer_type"] = "frustum"
        return obj

    def _create_axis_object(self, name: str, size: float = 0.4) -> bpy.types.Object:
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = "ARROWS"
        obj.empty_display_size = size
        obj["visualizer_type"] = "axis"
        return obj

    # ------------------------------------------------------------------
    # Geometry updates

    def _update_mesh_geometry(self, obj: bpy.types.Object,
                              vertices: Iterable[Iterable[float]],
                              faces: Iterable[Iterable[int]]):
        mesh = obj.data
        mesh.clear_geometry()
        verts = [tuple(map(float, v)) for v in vertices]
        polys = [tuple(f) for f in faces]
        mesh.from_pydata(verts, [], polys)
        mesh.update()

    def _update_point_cloud_geometry(self, obj: bpy.types.Object,
                                     points: Iterable[Iterable[float]]):
        mesh = obj.data
        mesh.clear_geometry()
        verts = [tuple(map(float, v)) for v in points]
        mesh.from_pydata(verts, [], [])
        mesh.update()

    def _update_frustum_geometry(self, obj: bpy.types.Object,
                                 vertices: List[Tuple[float, float, float]],
                                 edges: List[Tuple[int, int]]):
        mesh = obj.data
        mesh.clear_geometry()
        mesh.from_pydata(vertices, edges, [])
        mesh.update()

    def _build_frustum(self, entry: dict) -> Tuple[List[Tuple[float, float, float]],
                                                   List[Tuple[int, int]]]:
        intrinsic = entry.get("intrinsics") or entry.get("intrinsic")
        width = entry.get("width", 640)
        height = entry.get("height", 480)
        near = entry.get("near", 0.01)
        far = entry.get("far", 1.0)

        fx = intrinsic[0][0]
        fy = intrinsic[1][1]
        cx = intrinsic[0][2]
        cy = intrinsic[1][2]

        def project(depth):
            corners = []
            for u, v in ((0, 0), (width, 0), (width, height), (0, height)):
                x = (u - cx) * depth / fx
                y = (v - cy) * depth / fy
                corners.append((x, -y, depth))
            return corners

        near_pts = project(near)
        far_pts = project(far)
        origin = (0.0, 0.0, 0.0)
        vertices = [origin] + near_pts + far_pts

        edges = [
            (0, 1), (0, 2), (0, 3), (0, 4),
            (1, 2), (2, 3), (3, 4), (4, 1),
            (5, 6), (6, 7), (7, 8), (8, 5),
            (1, 5), (2, 6), (3, 7), (4, 8),
        ]
        return vertices, edges

    # ------------------------------------------------------------------
    # Materials

    def _apply_material(self, obj: bpy.types.Object, color: str,
                        emission_strength: float = 0.0):
        material = self._get_or_create_material(color, emission_strength)
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

    def _apply_wire_material(self, obj: bpy.types.Object, color: str):
        material = self._get_or_create_material(color, emission_strength=2.0)
        obj.color = (*_hex_to_rgb(color), 1.0)
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

    def _get_or_create_material(self, color: str,
                                emission_strength: float = 0.0) -> bpy.types.Material:
        key = f"{color}_{emission_strength}"
        material = self._materials.get(key)
        if material:
            return material
        material = bpy.data.materials.new(name=f"Visualizer_{color}")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        output = nodes.new(type="ShaderNodeOutputMaterial")
        shader = nodes.new(type="ShaderNodeEmission" if emission_strength > 0 else "ShaderNodeBsdfPrincipled")
        rgb = _hex_to_rgb(color)
        if emission_strength > 0:
            shader.inputs["Color"].default_value = (*rgb, 1.0)
            shader.inputs["Strength"].default_value = emission_strength
        else:
            shader.inputs["Base Color"].default_value = (*rgb, 1.0)
            shader.inputs["Roughness"].default_value = 0.6
        links.new(shader.outputs[0], output.inputs[0])
        self._materials[key] = material
        return material

    # ------------------------------------------------------------------
    # Utility

    def _remove_stale(self, cache: Dict[str, bpy.types.Object], active: set):
        stale = [key for key in cache if key not in active]
        for key in stale:
            obj = cache.pop(key, None)
            if obj:
                self._visibility_cache.pop(obj.name, None)
            if obj and obj.name in self.collection.objects:
                self.collection.objects.unlink(obj)
            if obj:
                bpy.data.objects.remove(obj, do_unlink=True)


_GLOBAL_BRIDGE: Optional[BlenderSceneBridge] = None


def start(host: Optional[str] = None, interval: float = 1.0, step: Optional[int] = None):
    """Start a global bridge instance (useful from the Blender GUI)."""
    global _GLOBAL_BRIDGE  # pylint: disable=global-statement
    if _GLOBAL_BRIDGE is None:
        _GLOBAL_BRIDGE = BlenderSceneBridge(host=host)
    _GLOBAL_BRIDGE.start_polling(interval=interval, step=step)
    return _GLOBAL_BRIDGE


def stop():
    """Stop the global bridge if it exists."""
    global _GLOBAL_BRIDGE  # pylint: disable=global-statement
    if _GLOBAL_BRIDGE is None:
        return
    _GLOBAL_BRIDGE.stop_polling()
    _GLOBAL_BRIDGE = None
