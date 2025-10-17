import time
import numpy as np
import trimesh
from viewer_client import Online3DViewer
import colorsys

def normalize(v):
    return v / np.linalg.norm(v)

def look_at(camera_position, target_position, up=np.array([0, 1, 0])):
    forward = normalize(target_position - camera_position)
    right = normalize(np.cross(forward, up))
    true_up = np.cross(right, forward)

    pose = np.eye(4)
    pose[:3, :3] = np.stack([right, true_up, forward], axis=1)
    pose[:3, 3] = camera_position
    return pose

# === Load and center mesh ===
mesh_path = "demo/bunny/reconstruction/bun_zipper_res3.ply"
mesh = trimesh.load(mesh_path)
centered = mesh.copy()
centered.apply_translation(-mesh.bounding_box.centroid)  # center at origin
initial_center = np.zeros(3)

# === Prepare viewer ===
viewer = Online3DViewer()
viewer.clear_scene()

# Point cloud (downsampled)
pointcloud = centered.vertices
if pointcloud.shape[0] > 2000:
    idx = np.random.choice(pointcloud.shape[0], 2000, replace=False)
    pointcloud = pointcloud[idx]

# Seed frame 0 with the reference mesh, origin axis, and point cloud
viewer.add_mesh(centered, label="bunny_reference", commit=False)
viewer.add_object_axis(np.eye(4), label="origin", commit=False)
viewer.add_point_cloud(pointcloud, color="#66ccff")
viewer.add_global_axes()

# === Known view (red frustum) ===
known_pose = look_at(np.array([0.5, 0.5, 0.5]), initial_center)
viewer.add_frustum(known_pose, color="#ff0000", visualize_orientation=True)

# === Simulate orbiting updated meshes ===
print("Starting orbit demo...")

radius = 1
num_orbits = 25

for i in range(num_orbits):
    print(f"[Demo] Iteration {i + 1}")
    
    theta = 2 * np.pi * i / num_orbits
    updated_pos = np.array([
        radius * np.cos(theta),
        0.0,
        radius * np.sin(theta)
    ])

    # Move the mesh to new position
    rotated = centered.copy()
    rotated.apply_transform(trimesh.transformations.rotation_matrix(angle=-theta, direction=np.array([0, 1, 0])))
    rotated.apply_translation(updated_pos)

    # Add orbiting frustum / mesh / axis for this step
    cam_pos = updated_pos + np.array([0.2, 0.2, 0.2])  # offset from object
    cam_pose = look_at(cam_pos, updated_pos)
    rainbow = "#{:02x}{:02x}{:02x}".format(*[int(255 * x) for x in colorsys.hsv_to_rgb(i / num_orbits, 1, 1)])

    viewer.add_mesh(rotated, commit=False)
    axis_pose = np.eye(4)
    axis_pose[:3, 3] = updated_pos
    viewer.add_object_axis(axis_pose, label=f"orbit_axis_{i+1}", commit=False)
    viewer.add_frustum(cam_pose, color=rainbow, visualize_orientation=True)

    time.sleep(0.5)

print("Done.")
