import time
import numpy as np
import trimesh
from viewer_client import Online3DViewer
import colorsys

def safe_normalize(v, eps=1e-8):
    norm = np.linalg.norm(v)
    if norm < eps:
        return np.zeros_like(v)
    return v / norm

def look_at(camera_position, target_position, up=np.array([0, 1, 0])):
    camera_position = np.asarray(camera_position, dtype=np.float64)
    target_position = np.asarray(target_position, dtype=np.float64)
    up = np.asarray(up, dtype=np.float64)

    forward = target_position - camera_position
    forward = safe_normalize(forward)
    if not np.any(forward):
        forward = np.array([0.0, 0.0, -1.0])

    up_vec = safe_normalize(up)
    if not np.any(up_vec):
        up_vec = np.array([0.0, 1.0, 0.0])

    if abs(np.dot(forward, up_vec)) > 0.999:
        candidate_axes = [np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])]
        for candidate in candidate_axes:
            if abs(np.dot(forward, candidate)) < 0.999:
                up_vec = candidate
                break
        up_vec = safe_normalize(up_vec)

    right = np.cross(forward, up_vec)
    right = safe_normalize(right)
    if not np.any(right):
        right = np.array([1.0, 0.0, 0.0])

    true_up = np.cross(right, forward)
    true_up = safe_normalize(true_up)

    pose = np.eye(4)
    pose[:3, :3] = np.stack([right, true_up, forward], axis=1)
    pose[:3, 3] = camera_position
    return pose

# === Load and center mesh ===
mesh_path = "demo/bunny/reconstruction/bun_zipper_res3.ply"
mesh = trimesh.load(mesh_path)
centered = mesh.copy()
centered.apply_translation(-mesh.bounding_box.centroid)
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

# Seed frame 0
viewer.step = 0
viewer.add_mesh(centered, label="bunny_mesh_0", color="#f8b400", commit=False)
viewer.add_object_axis(np.eye(4), label="bunny_axis_0", commit=False)
viewer.add_point_cloud(pointcloud, color="#66ccff", label="bunny_points_0", commit=False)
viewer.add_global_axes()

# Known view
known_pose = look_at(np.array([0.6, 0.6, 0.6]), initial_center)
viewer.add_frustum(known_pose, color="#ff5555", visualize_orientation=True, commit=False)

print("Starting orbit demo with animated mesh, axes, point clouds, and frustums...")

radius = 1.1
num_steps = 36
spin_angles = np.linspace(0.0, 2 * np.pi, num_steps, endpoint=False)

for step_idx, theta in enumerate(spin_angles, start=1):
    viewer.step = step_idx

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
    viewer.add_mesh(dynamic_mesh, label=f"bunny_mesh_{step_idx}", color="#f8b400", commit=False)

    ax_pose = np.eye(4)
    ax_pose[:3, :3] = (spin_matrix @ tilt_matrix)[:3, :3]
    ax_pose[:3, 3] = orbit_position
    viewer.add_object_axis(ax_pose, label=f"bunny_axis_{step_idx}", commit=False)

    highlight_points = (highlight_base @ mesh_transform.T)[:, :3]
    viewer.add_point_cloud(highlight_points, color="#ffcc00", label=f"bunny_highlight_{step_idx}", commit=False)

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
    viewer.add_frustum(top_pose, color="#44aaff", visualize_orientation=False, commit=False)

    print(f"[Demo] Step {step_idx}/{num_steps} -> radius={radius:.2f}, scale={scale_factor:.2f}")
    time.sleep(0.15)

viewer.step = num_steps + 1
print(f"Demo complete. Scrub the Blender timeline (frames 0..{num_steps}) to revisit each step.")
