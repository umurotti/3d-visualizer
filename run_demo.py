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

highlight_count = min(400, pointcloud.shape[0])
highlight_idx = np.linspace(0, pointcloud.shape[0] - 1, highlight_count, dtype=int)
highlight_base = np.hstack([pointcloud[highlight_idx], np.ones((highlight_count, 1))])

# Seed frame 0 with the reference mesh, origin axis, and point cloud
viewer.add_mesh(centered, label="bunny_mesh", color="#f8b400", commit=False)
viewer.add_object_axis(np.eye(4), label="bunny_axis", commit=False)
viewer.add_point_cloud(pointcloud, color="#66ccff", label="bunny_points", commit=False)
viewer.add_global_axes()

# === Known view (red frustum) ===
known_pose = look_at(np.array([0.6, 0.6, 0.6]), initial_center)
viewer.add_frustum(known_pose, color="#ff5555", visualize_orientation=True)

# === Advanced orbit demo ===
print("Starting orbit demo with animated mesh, axes, point clouds, and frustums...")

radius = 1.1
num_steps = 36
spin_angles = np.linspace(0.0, 2 * np.pi, num_steps, endpoint=False)

for step_idx, theta in enumerate(spin_angles, start=1):
    scale_factor = 1.0 + 0.12 * np.sin(theta * 3.0)
    tilt_angle = 0.35 * np.sin(theta * 2.0)
    orbit_height = 0.2 * np.sin(theta * 1.5)
    orbit_position = np.array([
        radius * np.cos(theta),
        orbit_height,
        radius * np.sin(theta)
    ])

    scale_matrix = trimesh.transformations.scale_matrix(scale_factor)
    tilt_matrix = trimesh.transformations.rotation_matrix(tilt_angle, [1, 0, 0])
    spin_matrix = trimesh.transformations.rotation_matrix(theta, [0, 1, 0])
    translation_matrix = trimesh.transformations.translation_matrix(orbit_position)

    mesh_transform = trimesh.transformations.concatenate_matrices(
        translation_matrix,
        spin_matrix,
        tilt_matrix,
        scale_matrix
    )

    dynamic_mesh = centered.copy()
    dynamic_mesh.apply_transform(mesh_transform)
    viewer.add_mesh(dynamic_mesh, label="bunny_mesh", color="#f8b400", commit=False)

    ax_pose = np.eye(4)
    ax_pose[:3, :3] = (spin_matrix @ tilt_matrix)[:3, :3]
    ax_pose[:3, 3] = orbit_position
    viewer.add_object_axis(ax_pose, label="bunny_axis", commit=False)

    highlight_points = (highlight_base @ mesh_transform.T)[:, :3]
    viewer.add_point_cloud(highlight_points, color="#ffcc00", label="bunny_highlight", commit=False)

    cam_offset = np.array([
        0.8 * np.cos(theta + np.pi / 3),
        0.35 + 0.15 * np.cos(theta * 1.3),
        0.8 * np.sin(theta + np.pi / 3)
    ])
    chase_pose = look_at(orbit_position + cam_offset, orbit_position)
    hue = (step_idx % num_steps) / num_steps
    rainbow = "#{:02x}{:02x}{:02x}".format(*[int(255 * c) for c in colorsys.hsv_to_rgb(hue, 0.9, 1.0)])
    viewer.add_frustum(chase_pose, color=rainbow, visualize_orientation=True, commit=False)

    top_pose = look_at(orbit_position + np.array([0.0, 1.6, 0.0]), orbit_position)
    viewer.add_frustum(top_pose, color="#44aaff", visualize_orientation=False)

    print(f"[Demo] Step {step_idx}/{num_steps} -> radius={radius:.2f}, scale={scale_factor:.2f}")
    time.sleep(0.15)

print(f"Demo complete. Scrub the Blender timeline (frames 0..{num_steps}) to revisit each step.")
