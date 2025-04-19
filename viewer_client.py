import numpy as np
import torch
import requests
import trimesh
import aiohttp

class Online3DViewer:
    def __init__(self, host=None, timeout=1):
        if host is not None:
            self.host = host
        else:
            try:
                with open("port.txt", "r") as f:
                    port = f.read().strip()
            except Exception as e:
                port = 5000
                print(f"Could not read viewer port from port.txt: {e}")
            finally:
                self.host = f"http://localhost:{port}"
                print(f"Using viewer host: {self.host}")
        self.timeout = timeout

    def load_scene(self, mesh=None, pointcloud=None):
        payload = {}

        if pointcloud is not None:
            if isinstance(pointcloud, torch.Tensor):
                pointcloud = pointcloud.detach().cpu().numpy()
            payload["points"] = pointcloud.tolist()

        if mesh is not None and isinstance(mesh, trimesh.Trimesh):
            payload["mesh"] = {
                "vertices": mesh.vertices.tolist(),
                "faces": mesh.faces.tolist()
            }

        try:
            requests.post(f"{self.host}/load_scene", json=payload, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not load scene: {e}")

    def add_frustum(self, pose, color="#00ff00"):
        if isinstance(pose, torch.Tensor):
            pose = pose.detach().cpu().numpy()
        elif not isinstance(pose, np.ndarray):
            raise ValueError("Pose must be a 4x4 numpy array or torch.Tensor")
        data = {"pose": pose.tolist(), "color": color}
        try:
            requests.post(f"{self.host}/add_frustum", json=data, timeout=1)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not add frustum: {e}")

    def add_object_axis(self, pose, label="Object"):
        if isinstance(pose, torch.Tensor):
            pose = pose.detach().cpu().numpy()
        elif not isinstance(pose, np.ndarray):
            raise ValueError("Pose must be a 4x4 numpy array or torch.Tensor")

        try:
            requests.post(f"{self.host}/add_object_axis", json={
                "pose": pose.tolist(),
                "label": label
            }, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not add object axis: {e}")

    def add_global_axes(self):
        try:
            requests.post(f"{self.host}/add_global_axes", timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not enable global axes: {e}")

    def add_mesh(self, mesh, label="updated"):
        if not isinstance(mesh, trimesh.Trimesh):
            raise ValueError("Expected a trimesh.Trimesh object")

        mesh_data = {
            "vertices": mesh.vertices.tolist(),
            "faces": mesh.faces.tolist()
        }

        try:
            requests.post(f"{self.host}/add_mesh", json={
                "mesh": mesh_data,
                "label": label
            }, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not add mesh: {e}")

    def clear_scene(self):
        """Clear all scene elements: point cloud, frustums, axes, and meshes."""
        try:
            requests.post(f"{self.host}/clear_scene", timeout=1)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not clear scene: {e}")