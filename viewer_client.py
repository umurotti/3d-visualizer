import numpy as np
import torch
import requests
import trimesh

class Online3DViewer:
    def __init__(self, host=None, timeout=50):
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
        self.step = 0
        self.clear_scene()

    def add_mesh(self, mesh, commit=True, color="#00ff00"):
        if not isinstance(mesh, trimesh.Trimesh):
            raise ValueError("Expected a trimesh.Trimesh object")

        mesh_data = {
            "vertices": mesh.vertices.tolist(),
            "faces": mesh.faces.tolist()
        }

        try:
            requests.post(f"{self.host}/add_mesh", json={
                "mesh": mesh_data,
                "color": color,
                "step": self.step
            }, timeout=self.timeout)
            if commit:
                self.step += 1
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not add mesh: {e}")
            
    def add_point_cloud(self, pointcloud, commit=True, color="#00ff00"):
        if isinstance(pointcloud, torch.Tensor):
            pointcloud = pointcloud.detach().cpu().numpy()
        elif not isinstance(pointcloud, np.ndarray):
            raise ValueError("Expected a numpy array or torch.Tensor")

        try:
            requests.post(f"{self.host}/add_point_cloud", json={
                "points": pointcloud.tolist(),
                "color": color,
                "step": self.step
            }, timeout=self.timeout)
            if commit:
                self.step += 1
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not add point cloud: {e}")
    
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

    def add_frustum(self, pose=np.eye(4), intrinsic=np.array([
                                                    [500,   0, 320],
                                                    [  0, 500, 240],
                                                    [  0,   0,   1]
                                                    ], dtype=np.float32), image_resolution=(640, 480), near=0.0, far=0.1, color="#00ff00", visualize_orientation=False, commit=True):
        # Check if pose is a 4x4 matrix
        if isinstance(pose, torch.Tensor):
            pose = pose.detach().cpu().numpy()
        elif not isinstance(pose, np.ndarray):
            raise ValueError("Pose must be a 4x4 numpy array or torch.Tensor")
        
        # Check if intrinsic is 3x3
        if isinstance(intrinsic, torch.Tensor):
            intrinsic = intrinsic.detach().cpu().numpy()
        elif not isinstance(intrinsic, np.ndarray):
            raise ValueError("Intrinsics must be a 4x4 numpy array or torch.Tensor")
        
        # Check if image_resolution is a tuple of (width, height)
        if isinstance(image_resolution, tuple) and len(image_resolution) == 2:
            width, height = image_resolution
        else:
            raise ValueError("Image resolution must be a tuple of (width, height)")
        
        # Check if near and far are numeric values
        if not isinstance(near, (int, float)) or not isinstance(far, (int, float)):
            raise ValueError("Near and far must be numeric values")
        
        data = {
                "pose": pose.tolist(),
                "intrinsic": intrinsic.tolist(),
                "width": width,
                "height": height,
                "near": near,
                "far": far,
                "color": color,
                "visualize_orientation": visualize_orientation,
                "step": self.step
                }
        try:
            requests.post(f"{self.host}/add_frustum", json=data, timeout=1)
            if commit:
                self.step += 1
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not add frustum: {e}")

    def add_object_axis(self, pose=np.eye(4), commit=True):
        if isinstance(pose, torch.Tensor):
            pose = pose.detach().cpu().numpy()
        elif not isinstance(pose, np.ndarray):
            raise ValueError("Pose must be a 4x4 numpy array or torch.Tensor")

        try:
            requests.post(f"{self.host}/add_object_axis", json={
                "pose": pose.tolist(),
                "step": self.step
            }, timeout=self.timeout)
            if commit:
                self.step += 1
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not add object axis: {e}")

    def add_global_axes(self):
        try:
            requests.post(f"{self.host}/add_global_axes", timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not enable global axes: {e}")

    def clear_scene(self):
        """Clear all scene elements: point cloud, frustums, axes, and meshes."""
        try:
            self.step = 0
            requests.post(f"{self.host}/clear_scene", timeout=1)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Could not clear scene: {e}")