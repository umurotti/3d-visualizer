import numpy as np
import torch
import requests
import trimesh

class Online3DViewer:
    def __init__(self, host="http://localhost:5006", timeout=1):
        self.host = host
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
